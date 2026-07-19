const { Cheque } = require("./cheque");
const { ERC20Token } = require("./erc20");
const consts = require("./const");

module.exports = {
  Cheque,
  ERC20Token,
  ...consts,
};
