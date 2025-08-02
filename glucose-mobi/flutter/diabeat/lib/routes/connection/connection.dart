import 'package:diabeat/nav.dart';
import 'package:diabeat/routes/connection/prefs.dart' as prefs;
import 'package:flutter/material.dart';

String? _addr;

void connectTo(String addr) {
  _addr = addr;
  prefs.writeAddr(addr);
}

bool get existAddr => _addr != null;

String get addr => _addr!;

Future<bool> connect(BuildContext context) async {
  if (existAddr) {
    return true;
  }

  if (await prefs.existAddr()) {
    connectTo(await prefs.readAddr());
    return true;
  }

  if (!context.mounted) {
    return false;
  }

  return await Navigator.pushNamed(context, '/scanner') == ScannerPageNav.ok;
}
