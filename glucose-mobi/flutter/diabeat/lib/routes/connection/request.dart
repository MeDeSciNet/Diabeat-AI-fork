import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

typedef JsonMap = Map<String, dynamic>;

class Request {
  Request._();
  static final _prefs = SharedPreferencesAsync();
  static final Dio _dio = Dio(
    BaseOptions(
      sendTimeout: const Duration(seconds: 1),
      validateStatus: (status) {
        return status != null && status >= 200 && status < 300;
      },
    ),
  );
  static late String? _addr;

  static Future<void> init() async {
    _addr = await _prefs.getString('addr');

    if (_addr != null) {
      _dio.options.baseUrl = 'http://$_addr:8000/api';
    }
  }

  static Future<void> setAddr(String value) async {
    _addr = value;
    _dio.options.baseUrl = 'http://$value:8000/api';
    await _prefs.setString('addr', value);
  }

  static Future<void> _tryConnect(BuildContext context) async {
    if (_addr != null) return;

    if (await _DisconnectedDialog.show(context) == null) {
      throw DisconnectedException();
    }
  }

  static Future<Response<JsonMap>> logIn(
    BuildContext context, {
    required String email,
    required String password,
  }) async {
    await _tryConnect(context);

    return await _dio.post<JsonMap>(
      '/token/',
      data: {'username_or_email': email, 'password': password},
    );
  }

  static Future<Response<JsonMap>> register(
    BuildContext context, {
    required String email,
    required String username,
    required String password,
  }) async {
    await _tryConnect(context);

    return await _dio.post<JsonMap>(
      '/register/',
      data: {'email': email, 'username': username, 'password': password},
    );
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

class DisconnectedException implements Exception {}
