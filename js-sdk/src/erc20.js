const { ethers } = require("ethers");
const { ERC20_ABI } = require("./const");

class ERC20Token {
  constructor({ provider, privateKey, signer, buildTx = false, tokenAddress, owner } = {}) {
    this.provider = provider;
    this.privateKey = privateKey;
    this.signer = signer;
    this.buildTx = buildTx;
    this.owner = owner;
    this.address = null;
    this.contract = null;
    if (tokenAddress) this.setParams({ tokenAddress });
  }

  // Prefers an explicit private key (Node/back-end usage); falls back to a
  // pre-connected signer (e.g. BrowserProvider.getSigner() from a wallet extension).
  _signer(privateKey) {
    const key = privateKey || this.privateKey;
    if (key) return new ethers.Wallet(key, this.provider);
    if (this.signer) return this.signer;
    throw new Error("No private key or signer provided");
  }

  setParams({ tokenAddress, provider } = {}) {
    if (provider) this.provider = provider;
    if (tokenAddress) {
      this.address = ethers.getAddress(tokenAddress);
      this.contract = new ethers.Contract(this.address, ERC20_ABI, this.provider);
    }
  }

  _ensureContract() {
    if (!this.contract) throw new Error("Token address is not set. Use setParams first.");
  }

  async getDecimals() {
    this._ensureContract();
    return Number(await this.contract.decimals());
  }

  async getSymbol() {
    this._ensureContract();
    return this.contract.symbol();
  }

  async getBalance(walletAddress = this.owner, decimals = null) {
    this._ensureContract();
    if (decimals === null) decimals = await this.getDecimals();
    const raw = await this.contract.balanceOf(ethers.getAddress(walletAddress));
    return {
      balance: raw,
      balance_ui: Number(raw) / 10 ** decimals,
      decimals,
    };
  }

  async allowance(spender, owner = this.owner) {
    this._ensureContract();
    return this.contract.allowance(ethers.getAddress(owner), ethers.getAddress(spender));
  }

  async approve(spender, amount, privateKey = this.privateKey, from) {
    this._ensureContract();

    if (this.buildTx) {
      const fromAddress = from ? ethers.getAddress(from) : ethers.computeAddress(privateKey || this.privateKey);
      const tx = await this.contract.approve.populateTransaction(ethers.getAddress(spender), amount);
      tx.from = fromAddress;
      return { tx };
    }

    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);
    const txResponse = await contract.approve(ethers.getAddress(spender), amount);
    const receipt = await txResponse.wait();
    if (receipt.status !== 1) throw new Error(`approve failed.\n ${txResponse.hash}`);
    return { tx: txResponse.hash };
  }

  async transfer(to, amount, privateKey = this.privateKey) {
    this._ensureContract();
    const signer = this._signer(privateKey);
    const contract = this.contract.connect(signer);

    if (this.buildTx) {
      const tx = await contract.transfer.populateTransaction(ethers.getAddress(to), amount);
      return { tx };
    }

    const txResponse = await contract.transfer(ethers.getAddress(to), amount);
    await txResponse.wait();
    return { tx: txResponse.hash };
  }
}

module.exports = { ERC20Token };
