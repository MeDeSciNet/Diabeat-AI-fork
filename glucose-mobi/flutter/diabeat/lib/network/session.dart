import 'package:diabeat/network/prefs.dart' as prefs;

prefs.Session? _session;

String get email => _session!.email;
String get username => _session!.username;
String get accessToken => _session!.accessToken;
String get refreshToken => _session!.refreshToken;

Future<bool> load() async {
  if (await prefs.existSession()) {
    final session = await prefs.readSession();
    _session = (
      email: session.email,
      username: session.username,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    );
    return true;
  }
  return false;
}

void save({
  required String email,
  required String username,
  required String accessToken,
  required String refreshToken,
}) {
  _session = (
    email: email,
    username: username,
    accessToken: accessToken,
    refreshToken: refreshToken,
  );

  prefs.writeSession(
    email: email,
    username: username,
    accessToken: accessToken,
    refreshToken: refreshToken,
  );
}

void delete() {
  _session = null;
  prefs.deleteSession();
}
