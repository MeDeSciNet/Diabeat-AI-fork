import 'package:shared_preferences/shared_preferences.dart';

class Prefs {
  static final _prefs = SharedPreferencesAsync();

  static Future<String?> getAddr() async {
    return await _prefs.getString('addr');
  }

  static Future<void> setAddr(String value) async {
    await _prefs.setString('addr', value);
  }

  static Future<String?> getEmail() async {
    return await _prefs.getString('email');
  }

  static Future<void> setEmail(String value) async {
    await _prefs.setString('email', value);
  }
}
