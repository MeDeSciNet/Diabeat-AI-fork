import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:diabeat/routes/network/connection.dart' as connection;

prefs.Session? _session;

String get email => _session!.email;
String get username => _session!.username;
String get accessToken => _session!.accessToken;
String get refreshToken => _session!.refreshToken;

Future<bool> loadAndLoad() async {
  if (!await prefs.existSession()) {
    return false;
  }

  final session = await prefs.readSession();
  _session = (
    email: session.email,
    username: session.username,
    accessToken: session.accessToken,
    refreshToken: session.refreshToken,
  );

  await connection.load();

  return true;
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
