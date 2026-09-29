// Remotion 4.0.529 binds all interfaces by default. Constrain this process's
// TCP listeners to loopback without changing node_modules or Windows firewall.
const net = require('node:net');
const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function (...args) {
  if (args[0] === undefined || args[0] === null) {
    args[0] = {port: 0, host: '127.0.0.1'};
  } else if (typeof args[0] === 'object' && args[0] !== null && 'port' in args[0]) {
    args[0] = {...args[0], port: args[0].port ?? 0, host: '127.0.0.1'};
  } else if (typeof args[0] === 'number') {
    const [port, ...rest] = args;
    if (typeof rest[0] === 'string') rest.shift();
    args = [{port, host: '127.0.0.1'}, ...rest];
  } else {
    throw new Error('Unexpected Studio listener: refusing to expose a non-loopback server');
  }
  return listen.apply(this, args);
};
const cli = require.resolve('@remotion/cli/package.json').replace(/package\.json$/, 'remotion-cli.js');
process.argv = [process.execPath, cli, 'studio', 'src/index.tsx', '--port=3100', ...process.argv.slice(2)];
require(cli);
