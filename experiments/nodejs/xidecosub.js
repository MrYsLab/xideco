// This is a simple JavaScript Xideco Bridge that subscribes to
// Scratch control messages destined for board #1.

var zmq = require('zmq')
  , sock = zmq.socket('sub');

var msgpack = require("msgpack-lite");
var data;

// remember to set ip address to the same ip address that the router uses.
sock.connect('tcp://192.168.2.101:43125');
sock.subscribe('A1');
console.log('Subscriber connected to port 43125');

sock.on('message', function(topic, message) {
  data = msgpack.decode(message);
  console.log('received a message related to:', topic, 'containing message:', data);

});

