import 'package:diabeat/routes/network/dialog/disconnected_dialog.dart';
import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:flutter/material.dart';

String? _addr;
void connectTo(String addr) {
  _addr = addr;
  prefs.writeAddr(addr);
}

bool get existAddr => _addr != null;
String get addr => _addr!;
Uri makeUrl(String path) {
  return Uri.http('$addr:8000', '/api$path/');
}

Future<bool> tryConnect(BuildContext context) async {
  if (existAddr) {
    return true;
  }

  if (await prefs.existAddr()) {
    connectTo(await prefs.readAddr());
    return true;
  }

  return context.mounted && await DisconnectedDialog.show(context) == true;
}
