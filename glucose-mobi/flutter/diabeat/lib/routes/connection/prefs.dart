import 'package:shared_preferences/shared_preferences.dart';

class Prefs {
  static final _prefs = SharedPreferencesAsync();

  static Future<String?> getAddr() async {
    return await _prefs.getString('addr');
  }

  static void setAddr(String value) {
    _prefs.setString('addr', value);
  }

  static Future<String?> getEmail() async {
    return await _prefs.getString('email');
  }

  static void setEmail(String value) {
    _prefs.setString('email', value);
  }
}
