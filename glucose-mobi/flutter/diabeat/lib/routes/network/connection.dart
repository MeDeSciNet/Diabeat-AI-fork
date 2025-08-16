import 'package:diabeat/routes/network/prefs.dart' as prefs;

String? _addr;

bool get existAddr => _addr != null;
String get addr => _addr!;
Uri makeUrl(String path) {
  return Uri.http('$addr:8000', '/api$path/');
}

Future<bool> load() async {
  if (await prefs.existAddr()) {
    _addr = await prefs.readAddr();
    return true;
  }
  return false;
}

void save(String addr) {
  _addr = addr;
  prefs.writeAddr(addr);
}
