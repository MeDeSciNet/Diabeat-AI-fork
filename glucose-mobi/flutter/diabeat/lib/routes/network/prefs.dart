import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final _prefs = SharedPreferencesAsync();

Future<String?> _readRawAddr() {
  return _prefs.getString('addr');
}

Future<bool> existAddr() async {
  return await _readRawAddr() != null;
}

Future<String> readAddr() async {
  return (await _readRawAddr())!;
}

void writeAddr(String addr) {
  _prefs.setString('addr', addr);
}

/* */
/* */
/* ===== Encrypted Shared Prefs ===== */

final _encryptedPrefs = const FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

Future<String?> _readRawRefreshToken() {
  return _encryptedPrefs.read(key: 'refresh_token');
}

Future<bool> existRefreshToken() async {
  return await _readRawRefreshToken() != null;
}

Future<String> readRefreshToken() async {
  return (await _readRawRefreshToken())!;
}

void writeRefreshToken(String refreshToken) {
  _encryptedPrefs.write(key: 'refresh_token', value: refreshToken);
}

void deleteRefreshToken() {
  _encryptedPrefs.delete(key: 'refresh_token');
}
