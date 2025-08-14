import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final _prefs = SharedPreferencesAsync();

Future<String?> _rawAddr() {
  return _prefs.getString('addr');
}

Future<bool> existAddr() async {
  return await _rawAddr() != null;
}

Future<String> readAddr() async {
  return (await _rawAddr())!;
}

void writeAddr(String addr) {
  _prefs.setString('addr', addr);
}

/* */
/* */
/* ===== Encrypted Shared Prefs ===== */

typedef Session = ({
  String email,
  String username,
  String accessToken,
  String refreshToken,
});

final _encryptedPrefs = const FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

Future<Session?> _rawSession() async {
  final email = await _encryptedPrefs.read(key: 'email');
  final username = await _encryptedPrefs.read(key: 'username');
  final accessToken = await _encryptedPrefs.read(key: 'access_token');
  final refreshToken = await _encryptedPrefs.read(key: 'refresh_token');

  return email == null
      ? null
      : (
          email: email,
          username: username!,
          accessToken: accessToken!,
          refreshToken: refreshToken!,
        );
}

Future<bool> existSession() async {
  return await _rawSession() != null;
}

Future<Session> readSession() async {
  return (await _rawSession())!;
}

void writeSession({
  required String email,
  required String username,
  required String accessToken,
  required String refreshToken,
}) {
  _encryptedPrefs
    ..write(key: 'email', value: email)
    ..write(key: 'username', value: username)
    ..write(key: 'access_token', value: accessToken)
    ..write(key: 'refresh_token', value: refreshToken);
}

void deleteSession() {
  _encryptedPrefs.deleteAll();
}
