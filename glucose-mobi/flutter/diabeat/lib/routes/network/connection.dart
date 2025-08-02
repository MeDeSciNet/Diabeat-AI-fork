import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:diabeat/routes/network/scanner.dart';
import 'package:flutter/material.dart';

String? _addr;

void connectTo(String addr) {
  _addr = addr;
  prefs.writeAddr(addr);
}

bool get existAddr => _addr != null;

String get addr => _addr!;

Uri makeUrl(String path) {
  return Uri.http('$addr:8000', path);
}

Future<bool> connect(BuildContext context) async {
  if (existAddr) {
    return true;
  }

  if (await prefs.existAddr()) {
    connectTo(await prefs.readAddr());
    return true;
  }

  return context.mounted &&
      await Navigator.pushNamed(context, '/scanner') == ScannerPageNav.ok;
}
