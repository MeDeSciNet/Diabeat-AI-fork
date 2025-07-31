import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Prefs {
  static final _prefs = SharedPreferencesAsync();
  static final _encryptedPrefs = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static Future<String?> getAddr() async {
    return await _prefs.getString('addr');
  }

  static void writeAddr(String value) {
    _prefs.setString('addr', value);
  }

  static Future<String?> getEncryptedRefreshToken() async {
    return await _encryptedPrefs.read(key: 'refresh_token');
  }

  static void writeEncryptedRefreshToken(String value) {
    _encryptedPrefs.write(key: 'refresh_token', value: value);
  }

  static void delEncryptedRefreshToken() {
    _encryptedPrefs.delete(key: 'refresh_token');
  }
}
