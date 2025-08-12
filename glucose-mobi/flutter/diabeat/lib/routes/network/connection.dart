import 'package:diabeat/routes/network/prefs.dart' as prefs;

String? _addr;

bool get existAddr => _addr != null;

String get addr => _addr!;

Uri makeUrl(String path) {
  return Uri.http('$addr:8000', '/api$path/');
}

void connectTo(String addr) {
  _addr = addr;
  prefs.writeAddr(addr);
}
