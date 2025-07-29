import 'package:diabeat/routes/connection/prefs.dart';
import 'package:diabeat/routes/connection/scanner.dart';
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
      connectTimeout: const Duration(seconds: 1),
      sendTimeout: const Duration(seconds: 3),
      receiveTimeout: const Duration(seconds: 3),
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

  /* */
  /* */
  /* */

  static Future<Response<T>> _handle<T>(
    BuildContext context,
    Future<Response<T>> Function() builder,
  ) async {
    if (_dio.options.baseUrl.isEmpty) {
      switch (await _DisconnectedDialog.show(context)) {
        case _DisconnectedDialogNav.ok:
          break;

        default:
          throw CancelConnectionException();
      }
    }

    bool loop = true;
    while (loop) {
      loop = false;

      try {
        return await builder();
      } on DioException catch (e) {
        switch (e.type) {
          case DioExceptionType.connectionTimeout:
          case DioExceptionType.sendTimeout:
          case DioExceptionType.receiveTimeout:
            if (!context.mounted) rethrow;
            switch (await _TimeoutDialog.show(context, e.type.toString())) {
              case _TimeoutDialogNav.retry:
                loop = true;
                break;

              default:
                rethrow;
            }

          default:
            rethrow;
        }
      }
    }

    throw Unreachable(); // this should not happen !
  }

  static Future<void> logIn(
    BuildContext context, {
    required String email,
    required String password,
    required bool rememberMe,
  }) async {
    final res = await _handle<JsonMap>(
      context,
      () => _dio.post(
        '/token/',
        data: {'username_or_email': email, 'password': password},
      ),
    );

    _session = (
      email: email,
      username: res.data!['username'],
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
    );

    if (rememberMe) {
      Prefs.setEmail(email);
    }
  }

  static Future<void> register(
    BuildContext context, {
    required String email,
    required String username,
    required String password,
    required bool rememberMe,
  }) async {
    final res = await _handle<JsonMap>(
      context,
      () => _dio.post(
        '/register/',
        data: {'email': email, 'username': username, 'password': password},
      ),
    );

    _session = (
      email: email,
      username: username,
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
    );

    if (rememberMe) {
      Prefs.setEmail(email);
    }
  }

  static void logOut() {
    _session = null;
  }
}

/* */
/* */
/* */

class CancelConnectionException implements Exception {}

class Unreachable implements Exception {}

enum _DisconnectedDialogNav { ok }

class _DisconnectedDialog extends StatelessWidget {
  const _DisconnectedDialog._();

  static Future show(BuildContext context) async {
    final nav = await showDialog(
      context: context,
      builder: (context) => const _DisconnectedDialog._(),
    );

    return switch (nav) {
      _DisconnectedDialogNav.ok when context.mounted =>
        switch (await Navigator.pushNamed(context, '/connection/scanner')) {
          ScannerPageNav.ok => _DisconnectedDialogNav.ok,
          _ => null,
        },
      _ => null,
    };
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
          DialogButtons.binary(
            text1: '取消',
            onPressed1: () {
              Navigator.pop(context, null);
            },
            text2: '連接',
            onPressed2: () {
              Navigator.pop(context, _DisconnectedDialogNav.ok);
            },
          ),
        ],
      ),
    );
  }
}

/* */
/* */
/* */

enum _TimeoutDialogNav { retry, _scan }

class _TimeoutDialog extends StatelessWidget {
  const _TimeoutDialog._(this.type);
  final String type;

  static Future show(BuildContext context, String type) async {
    final nav = await showDialog(
      context: context,
      builder: (context) => _TimeoutDialog._(type),
    );

    return switch (nav) {
      _TimeoutDialogNav.retry => _TimeoutDialogNav.retry,
      _TimeoutDialogNav._scan when context.mounted =>
        switch (await Navigator.pushNamed(context, '/connection/scanner')) {
          ScannerPageNav.ok => _TimeoutDialogNav.retry,
          _ => null,
        },
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Center(child: Text('請求狀態')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(type),
          DialogButtons.ternary(
            context,
            text1: '取消',
            onPressed1: () {
              Navigator.pop(context, null);
            },
            text2: '重試',
            onPressed2: () {
              Navigator.pop(context, _TimeoutDialogNav.retry);
            },
            text3: '連接',
            onPressed3: () {
              Navigator.pop(context, _TimeoutDialogNav._scan);
            },
          ),
        ],
      ),
    );
  }
}
