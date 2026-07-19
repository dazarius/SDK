const { ethers } = require("ethers");
const { ORBIS_CHEQUES_ABI, ORBIS_CHEQUES_CONTRACT, ALLOW_CHAINS, CHEQUES_TYPE, MAPS_FUNC, CODE_TO_TYPE } = require("./const");
const { ERC20Token } = require("./erc20");

function toBytes32(chequeId) {
  return ethers.zeroPadValue(ethers.hexlify(chequeId), 32);
}

class Cheque {
  constructor({ provider, privateKey, signer, abi = ORBIS_CHEQUES_ABI, allowedChains = ALLOW_CHAINS, returnBuildTx = true, address, contractAddress } = {}) {
    this.provider = provider;
    this.privateKey = privateKey;
    this.signer = signer;
    this.abi = abi;
    this.address = address;
    this.returnBuildTx = returnBuildTx;
    this.allowedChains = allowedChains;
    this.amount = null;
    this.token = null;
    this.contract = contractAddress ? new ethers.Contract(ethers.getAddress(contractAddress), abi, provider) : null;
  }

  // Cheque id is derived from a fresh random secret, not from sender/salt/time:
  // hash = keccak256(secret), then the last byte of the hash is overwritten
  // with MAPS_FUNC[type].code so the type can later be read back locally
  // (see _resolveChequeType) without hitting the contract.
  static generateChequeId(type) {
    const secret = ethers.randomBytes(32);
    const hash = ethers.keccak256(secret);
    const bytes = ethers.getBytes(hash);
    bytes[31] = MAPS_FUNC[type].code;
    const id = ethers.hexlify(bytes);
    return { secret: ethers.hexlify(secret), id };
  }

  static normalizeChequeId(chequeId) {
    if (chequeId instanceof Uint8Array || typeof chequeId === "string") {
      return toBytes32(chequeId);
    }
    throw new Error("chequeId must be bytes or a hex string");
  }

  async getId(txResponseOrHash) {
    let receipt;
    if (typeof txResponseOrHash === "string") {
      receipt = await this.provider.waitForTransaction(txResponseOrHash);
    } else {
      receipt = txResponseOrHash;
    }
    for (const log of receipt.logs) {
      try {
        const parsed = this.contract.interface.parseLog(log);
        if (parsed && parsed.name === "ChequeCreated") return parsed.args.id;
      } catch {
        // not a ChequeCreated log, skip
      }
    }
    return false;
  }

  async _ensureContract() {
    if (this.contract) return this.contract;
    if (!this.provider) throw new Error("Provider is not set");
    const network = await this.provider.getNetwork();
    const chainId = Number(network.chainId);
    if (!this.allowedChains.includes(chainId)) {
      throw new Error(`Chain ${chainId} is not allowed. Allowed chains are: ${this.allowedChains}`);
    }
    return this.getContractForChain(chainId);
  }

  getContractForChain(chainId) {
    const addr = ORBIS_CHEQUES_CONTRACT[Number(chainId)];
    if (!addr) {
      throw new Error(`Chain ${chainId} is not supported. Supported chains are: ${Object.keys(ORBIS_CHEQUES_CONTRACT)}`);
    }
    this.contract = new ethers.Contract(ethers.getAddress(addr), this.abi, this.provider);
    return this.contract;
  }

  async getAddress() {
    if (this.address) return this.address;
    throw new Error("No address provided");
  }

  setParameters({ provider, amount, privateKey, signer, token, address, contractAddress } = {}) {
    if (provider) this.provider = provider;
    if (contractAddress) this.contract = new ethers.Contract(ethers.getAddress(contractAddress), this.abi, this.provider);
    if (amount !== undefined) this.amount = amount;
    if (privateKey) {
      this.privateKey = privateKey;
      this.address = new ethers.Wallet(privateKey).address;
    }
    if (signer) this.signer = signer;
    if (token) this.token = token;
    if (address) this.address = address;
  }

  // Prefers an explicit private key (Node/back-end usage); falls back to a
  // pre-connected signer (e.g. BrowserProvider.getSigner() from a wallet extension).
  _signer(privateKey) {
    const key = privateKey || this.privateKey;
    if (key) return new ethers.Wallet(key, this.provider);
    if (this.signer) return this.signer;
    throw new Error("No private key or signer provided");
  }

  _resolveFrom(from, privateKey) {
    if (from) return ethers.getAddress(from);
    const key = privateKey || this.privateKey;
    if (key) return ethers.computeAddress(key);
    if (this.address) return ethers.getAddress(this.address);
    throw new Error("No from address, private key, or address provided");
  }

  // ── Type detection — shared by the CashOut / Refund dispatchers ───────────
  //
  // Fast path: IDs minted via generateChequeId() carry the type as the last
  // byte (see MAPS_FUNC[type].code), so the type is read locally with no
  // network call.
  // Slow path (fallback): for custom/legacy IDs with an unrecognized code,
  // walks MAPS_FUNC's "info" getters and returns the first type whose mapping
  // actually holds `chequeId` (a missing entry comes back zero-valued from
  // the contract rather than reverting, so existence is checked via the
  // zero-address / empty-array sentinel each getter returns).

  async _resolveChequeType(chequeId) {
    const idBytes = toBytes32(chequeId);
    const code = ethers.getBytes(idBytes)[31];
    const knownType = CODE_TO_TYPE[code];
    if (!knownType) throw new Error("Cheque not found for any known type");
  

    await this._ensureContract();

    return knownType;
  }

  // ── Dispatcher — picks Native / Multi / Token automatically ───────────────

  // Mirrors the contract's InitCheque dispatcher:
  //   - tokenAddress set     → token cheque (ERC-20), `to` must hold exactly 1 recipient
  //   - tokenAddress not set
  //       - to.length == 1    → native cheque (single recipient), funded by value
  //       - to.length > 1     → multi cheque, funded by value split across recipients
  // Extra `overrides` (gasLimit, nonce, etc.) are forwarded to the underlying
  // `Init*Cheque` call resolved from MAPS_FUNC.
  async InitCheque(amount, to, tokenAddress, privateKey, chequeId, from, overrides = {}) {
    if (!Array.isArray(to) || to.length === 0) {
      throw new Error("Recipients required");
    }

    if (tokenAddress) {
      if (to.length !== 1) {
        throw new Error("Token cheque supports a single recipient");
      }
      const method = this[MAPS_FUNC[CHEQUES_TYPE.TokenCheque].init];
      return method.call(this, tokenAddress, amount, to[0], privateKey, chequeId, from, overrides);
    }

    if (to.length === 1) {
      const method = this[MAPS_FUNC[CHEQUES_TYPE.NativeCheque].init];
      return method.call(this, amount, to[0], privateKey, chequeId, from, overrides);
    }

    const method = this[MAPS_FUNC[CHEQUES_TYPE.MultiCheque].init];
    return method.call(this, amount, to, privateKey, chequeId, from, overrides);
  }

  // ── Dispatcher — cashes out whichever type `chequeId` turns out to be ─────

  async CashOutCheque(chequeId, privateKey, overrides = {}) {
    const type = await this._resolveChequeType(chequeId);
    const method = this[MAPS_FUNC[type].cashout];
    return method.call(this, chequeId, privateKey, overrides);
  }

  // ── Native ETH cheque — single recipient ──────────────────────────────────

  async InitNativeCheque(amount, receiver, privateKey, chequeId, from, overrides = {}) {
    await this._ensureContract();
    const fromAddress = this._resolveFrom(from, privateKey);
    const receiverCs = ethers.getAddress(receiver);
    const { secret, id } = chequeId
      ? { secret: null, id: Cheque.normalizeChequeId(chequeId) }
      : Cheque.generateChequeId(CHEQUES_TYPE.NativeCheque);
    const valueWei = ethers.parseEther(String(amount));

    if (this.returnBuildTx) {
      const tx = await this.contract.InitNativeCheque.populateTransaction(id, receiverCs, { value: valueWei, ...overrides });
      tx.from = fromAddress;
      return { tx, id, secret, type: CHEQUES_TYPE.NativeCheque };
    }

    const contract = this.contract.connect(this._signer(privateKey));
    const txResponse = await contract.InitNativeCheque(id, receiverCs, { value: valueWei, ...overrides });
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id, secret, type: CHEQUES_TYPE.NativeCheque };
  }

  async CashOutNativeCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.CashOutNativeCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.CashOutNativeCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  // ── Native ETH cheque — multi recipient ───────────────────────────────────

  async InitMultiCheque(amount, receivers, privateKey, chequeId, from, overrides = {}) {
    if (!Array.isArray(receivers) || receivers.length === 0) {
      throw new Error("Receivers must be a non-empty list of addresses");
    }
    await this._ensureContract();
    const fromAddress = this._resolveFrom(from, privateKey);
    const receiversCs = receivers.map((r) => ethers.getAddress(r));
    const { secret, id } = chequeId
      ? { secret: null, id: Cheque.normalizeChequeId(chequeId) }
      : Cheque.generateChequeId(CHEQUES_TYPE.MultiCheque);
    const valueWei = ethers.parseEther(String(amount));

    if (this.returnBuildTx) {
      const tx = await this.contract.InitMultiCheque.populateTransaction(id, receiversCs, { value: valueWei, ...overrides });
      tx.from = fromAddress;
      return { tx, id, secret, type: CHEQUES_TYPE.MultiCheque };
    }

    const contract = this.contract.connect(this._signer(privateKey));
    const txResponse = await contract.InitMultiCheque(id, receiversCs, { value: valueWei, ...overrides });
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id, secret, type: CHEQUES_TYPE.MultiCheque };
  }

  async CashOutMultiCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.CashOutMultiCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.CashOutMultiCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  // ── ERC-20 token cheque ────────────────────────────────────────────────────

  async InitTokenCheque(tokenAddress, amount, receiver, privateKey, chequeId, from, overrides = {}) {
    await this._ensureContract();
    const fromAddress = this._resolveFrom(from, privateKey);
    const tokenCs = ethers.getAddress(tokenAddress);
    const receiverCs = ethers.getAddress(receiver);
    const { secret, id } = chequeId
      ? { secret: null, id: Cheque.normalizeChequeId(chequeId) }
      : Cheque.generateChequeId(CHEQUES_TYPE.TokenCheque);

    const erc20 = new ERC20Token({ provider: this.provider, signer: this.signer, tokenAddress: tokenCs, buildTx: this.returnBuildTx });
    const currentAllowance = await erc20.allowance(this.contract.target, fromAddress);
    if (currentAllowance < BigInt(amount)) {
      const approve = await erc20.approve(this.contract.target, amount, privateKey || this.privateKey, fromAddress);
      if (approve) return { need_approve: approve };
    }

    if (this.returnBuildTx) {
      const tx = await this.contract.InitTokenCheque.populateTransaction(id, tokenCs, amount, receiverCs, overrides);
      tx.from = fromAddress;
      return { tx, id, secret, type: CHEQUES_TYPE.TokenCheque };
    }

    const contract = this.contract.connect(this._signer(privateKey));
    const txResponse = await contract.InitTokenCheque(id, tokenCs, amount, receiverCs, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id, secret, type: CHEQUES_TYPE.TokenCheque };
  }

  async CashOutTokenCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.CashOutTokenCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.CashOutTokenCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  // ── Swap cheque ────────────────────────────────────────────────────────────

  async InitTokenChequeSwap(tokenIn, amountIn, tokenOut, amountOut, receiver, privateKey, chequeId, from, overrides = {}) {
    await this._ensureContract();
    const fromAddress = this._resolveFrom(from, privateKey);
    const tokenInCs = ethers.getAddress(tokenIn);
    const tokenOutCs = ethers.getAddress(tokenOut);
    const receiverCs = ethers.getAddress(receiver);
    const { secret, id } = chequeId
      ? { secret: null, id: Cheque.normalizeChequeId(chequeId) }
      : Cheque.generateChequeId(CHEQUES_TYPE.SwapCheque);

    const erc20 = new ERC20Token({ provider: this.provider, signer: this.signer, tokenAddress: tokenInCs, buildTx: this.returnBuildTx });
    const currentAllowance = await erc20.allowance(this.contract.target, fromAddress);
    if (currentAllowance < BigInt(amountIn)) {
      const approve = await erc20.approve(this.contract.target, amountIn, privateKey || this.privateKey, fromAddress);
      if (!approve) return false;
      if (this.returnBuildTx) return { need_approve: approve };
    }

    if (this.returnBuildTx) {
      const tx = await this.contract.InitSwapCheque.populateTransaction(id, receiverCs, tokenInCs, amountIn, tokenOutCs, amountOut, overrides);
      tx.from = fromAddress;
      return { tx, id, secret, type: CHEQUES_TYPE.SwapCheque };
    }

    const contract = this.contract.connect(this._signer(privateKey));
    const txResponse = await contract.InitSwapCheque(id, receiverCs, tokenInCs, amountIn, tokenOutCs, amountOut, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id, secret, type: CHEQUES_TYPE.SwapCheque };
  }

  async CashOutSwapCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const key = privateKey || this.privateKey;
    const swapDetail = await this._getSwapDetail(chequeId);
    const tokenOut = swapDetail.tokenOut;
    const amountOut = swapDetail.amountOut;

    const signer = this._signer(key);
    const fromAddress = await signer.getAddress();

    const erc20 = new ERC20Token({ provider: this.provider, signer: this.signer, tokenAddress: tokenOut });
    const currentAllowance = await erc20.allowance(this.contract.target, fromAddress);
    if (currentAllowance < amountOut) {
      const approve = await erc20.approve(this.contract.target, amountOut, key);
      if (!approve) return false;
    }

    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.CashOutSwapCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.CashOutSwapCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  // ── Refund cheque — sender reclaims funds after expiry ────────────────────
  //
  // Contract-side all four Refund*Cheque functions share one signature,
  // e.g. `function RefundNativeCheque(bytes32 chequeId)`. RefundCheque is the
  // single entry point mirroring that shape: it figures out which mapping
  // `chequeId` lives in and calls the matching internal refund.

  async RefundCheque(chequeId, privateKey, overrides = {}) {
    const type = await this._resolveChequeType(chequeId);

    if (type === CHEQUES_TYPE.NativeCheque) return this._refundNativeCheque(chequeId, privateKey, overrides);
    if (type === CHEQUES_TYPE.MultiCheque) return this._refundMultiCheque(chequeId, privateKey, overrides);
    if (type === CHEQUES_TYPE.TokenCheque) return this._refundTokenCheque(chequeId, privateKey, overrides);

    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.RefundSwapCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.RefundSwapCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  async _refundNativeCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.RefundNativeCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.RefundNativeCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  async _refundMultiCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.RefundMultiCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.RefundMultiCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  async _refundTokenCheque(chequeId, privateKey, overrides = {}) {
    await this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const idBytes = toBytes32(chequeId);

    if (this.returnBuildTx) {
      const tx = await contract.RefundTokenCheque.populateTransaction(idBytes, overrides);
      return { tx, id: chequeId };
    }

    const txResponse = await contract.RefundTokenCheque(idBytes, overrides);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) return false;
    return { tx: txResponse.hash, id: chequeId };
  }

  // ── Read functions ─────────────────────────────────────────────────────────

  async getComunityPool() {
    await this._ensureContract();
    return this.contract.getCollectedFee();
  }

  async getBalance() {
    await this._ensureContract();
    return this.contract.getBalance();
  }

  async getOwner() {
    await this._ensureContract();
    return this.contract.getOwner();
  }

  async getTreasery() {
    await this._ensureContract();
    return this.contract.getTreasery();
  }

  async getProtocolStats() {
    await this._ensureContract();
    const s = await this.contract.getProtocolStats();
    return {
      balance: s[0],
      collectedFees: s[1],
      nativeBps: s[2],
      multiBps: s[3],
      tokenBps: s[4],
      swapBps: s[5],
      feeDenominator: s[6],
      treasury: s[7],
      owner: s[8],
      active: s[9],
      nextWithdraw: s[10],
    };
  }

  async nextAvailableWithdraw() {
    await this._ensureContract();
    return this.contract.nextAvailableWithdraw();
  }
  // Dispatcher — detects the cheque's type and returns its formatted detail
  // via the matching `_get*ChequeInfo`/`_getSwapDetail` from MAPS_FUNC.
  async getChequeDetail(chequeId) {
    const type = await this._resolveChequeType(chequeId);
    const method = this[MAPS_FUNC[type].detail];
    const detail = await method.call(this, chequeId);
    return {  ...detail};
  }

  async _getNativeChequeInfo(chequeId) {
    if (!chequeId) throw new Error("Cheque ID is required");
    await this._ensureContract();
    const info = await this.contract.getNativeChequeInfo(toBytes32(chequeId));
    return { signer: info[0], recepient: info[1], amount: info[2], claimed: info[3], expiresAt: info[4] };
  }

  async _getMultiChequeInfo(chequeId, address) {
    if (!chequeId) throw new Error("Cheque ID is required");
    await this._ensureContract();
    const addr = address ? ethers.getAddress(address) : this.address;
    const info = await this.contract.getMultiChequeInfo(toBytes32(chequeId), addr);
    return { signer: info[0], recepients: info[1], amount: info[2], claimed: info[3], expiresAt: info[4] };
  }

  async _getTokenChequeInfo(chequeId) {
    if (!chequeId) throw new Error("Cheque ID is required");
    await this._ensureContract();
    const info = await this.contract.getTokenChequeDetail(toBytes32(chequeId));
    return { signer: info[0], recepient: info[1], token: info[2], amount: info[3], claimed: info[4],expiresAt: info[5] };
  }

  async _getSwapDetail(chequeId) {
    await this._ensureContract();
    const s = await this.contract.getSwapDetail(toBytes32(chequeId));
    return { signer: s[0], recepient: s[1], tokenIn: s[2], amountIn: s[3], tokenOut: s[4], amountOut: s[5], claimed: s[6], expiresAt: s[7] };
  }

  async getFees() {
    await this._ensureContract();
    const f = await this.contract.getFee();
    return { nativeBps: f[0], multiBps: f[1], tokenBps: f[2], swapBps: f[3], denominator: f[4]};

  }
}

module.exports = { Cheque, toBytes32 };
