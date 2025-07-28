import 'package:diabeat/routes/connection/prefs.dart';
import 'package:dio/dio.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

typedef JsonMap = Map<String, dynamic>;

typedef _Session = ({
  String email,
  String username,
  String accessToken,
  String refreshToken,
});

class Request {
  Request._();
  static final _dio = Dio(
    BaseOptions(
      sendTimeout: const Duration(seconds: 1),
      validateStatus: (status) {
        return status != null && status >= 200 && status < 300;
      },
    ),
  );
  static _Session? _session;
  static String get email => _session!.email;
  static String get username => _session!.username;

  static Future<void> init() async {
    final addr = await Prefs.getAddr();

    if (addr != null) {
      _dio.options.baseUrl = 'http://$addr:8000/api';
    }
  }

  static void setAddr(String value) {
    _dio.options.baseUrl = 'http://$value:8000/api';
    Prefs.setAddr(value);
  }

  //
  //
  //

  static Future<void> _checkConnection(BuildContext context) async {
    if (_dio.options.baseUrl.isNotEmpty) return;

    if (await _DisconnectedDialog.show(context) == null) {
      throw CancelConnectionException();
    }
  }

  static Future<void> logIn(
    BuildContext context, {
    required String email,
    required String password,
    required bool remeberMe,
  }) async {
    await _checkConnection(context);

    final res = await _dio.post<JsonMap>(
      '/token/',
      data: {'username_or_email': email, 'password': password},
    );

    _session = (
      email: email,
      username: res.data!['username'],
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
    );

    if (remeberMe) {
      Prefs.setEmail(email);
    }
  }

  static Future<void> register(
    BuildContext context, {
    required String email,
    required String username,
    required String password,
    required bool remeberMe,
  }) async {
    await _checkConnection(context);

    final res = await _dio.post<JsonMap>(
      '/register/',
      data: {'email': email, 'username': username, 'password': password},
    );

    _session = (
      email: email,
      username: username,
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
    );

    if (remeberMe) {
      Prefs.setEmail(email);
    }
  }

  static void logOut() {
    _session = null;
  }
}

class _DisconnectedDialog extends StatelessWidget {
  const _DisconnectedDialog._();

  static Future show(BuildContext context) async {
    var res = await showDialog(
      context: context,
      builder: (context) => const _DisconnectedDialog._(),
    );

    if (res == null || !context.mounted) {
      return null;
    }

    return await Navigator.pushNamed(context, '/connection/scanner');
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('連線狀態', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            '尚未連接到伺服器',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    Navigator.pop(context, null);
                  },
                  style: BtnStyleExt.dialogNeg,
                  child: const Text('取消'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton(
                  onPressed: () {
                    Navigator.pop(context, '!scan');
                  },
                  style: BtnStyleExt.dialogPos,
                  child: const Text('掃描'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class CancelConnectionException implements Exception {}
