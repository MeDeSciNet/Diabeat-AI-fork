import 'package:diabeat/routes/connection/prefs.dart' as prefs;

({String username, String accessToken, String refreshToken})? _session;

bool get loggedIn => _session != null;
String get username => _session!.username;
String get accessToken => _session!.accessToken;
String get refreshToken => _session!.refreshToken;

void save({
  required String username,
  required String accessToken,
  required String refreshToken,
}) {
  _session = (
    username: username,
    accessToken: accessToken,
    refreshToken: refreshToken,
  );
  prefs.writeRefreshToken(refreshToken);
}

void delete() {
  _session = null;
  prefs.deleteRefreshToken();
}
