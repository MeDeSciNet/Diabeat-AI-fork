import 'package:diabeat/routes/connection/prefs.dart';
import 'package:diabeat/routes/connection/scanner.dart';
import 'package:dio/dio.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

typedef JsonMap = Map<String, dynamic>;

typedef _Session = ({String username, String accessToken, String refreshToken});

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

  static bool get loggedIn => _session != null;

  static Future<void> init() async {
    final addr = await Prefs.getAddr();
    if (addr != null) {
      _dio.options.baseUrl = 'http://$addr:8000/api';
    }

    final oldRefreshToken = await Prefs.getEncryptedRefreshToken();
    if (oldRefreshToken != null) {
      await refresh(oldRefreshToken);
    }

    _dio.interceptors.add(_AuthInterceptor(_dio, () => _session!.accessToken));
  }

  static void setAddr(String value) {
    _dio.options.baseUrl = 'http://$value:8000/api';
    Prefs.setAddr(value);
  }

  static void logOut() {
    _session = null;
    Prefs.delEncryptedRefreshToken();
  }

  static Future<void> refresh([String? oldRefreshToken]) async {
    oldRefreshToken ??= _session!.refreshToken;

    final res = await _dio.post<JsonMap>(
      '/token/refresh/',
      data: {'refresh': oldRefreshToken},
    );
    final data = res.data!;

    _session = (
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
  }

  static Future<void> _tryConnect(BuildContext context) async {
    if (_dio.options.baseUrl.isNotEmpty) return;

    switch (await _DisconnectedDialog.show(context)) {
      case _DisconnectedDialogNav.ok:
        return;

      default:
        throw CancelConnectionException();
    }
  }

  static void _setSessionAndPrefs({
    required String email,
    required String username,
    required String accessToken,
    required String refreshToken,
    required bool rememberMe,
  }) {
    _session = (
      username: username,
      accessToken: accessToken,
      refreshToken: refreshToken,
    );

    if (rememberMe) {
      Prefs.setEmail(email);
      Prefs.setEncryptedRefreshToken(refreshToken);
    }
  }

  static Future<void> logIn(
    BuildContext context, {
    required String email,
    required String password,
    required bool rememberMe,
  }) async {
    await _tryConnect(context);

    final res = await _dio.post(
      '/token/',
      data: {'username_or_email': email, 'password': password},
      options: Options(extra: {'context': context}),
    );

    _setSessionAndPrefs(
      email: email,
      username: res.data!['username'],
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
      rememberMe: rememberMe,
    );
  }

  static Future<void> register(
    BuildContext context, {
    required String email,
    required String username,
    required String password,
    required bool rememberMe,
  }) async {
    await _tryConnect(context);

    final res = await _dio.post(
      '/register/',
      data: {'email': email, 'username': username, 'password': password},
      options: Options(extra: {'context': context}),
    );

    _setSessionAndPrefs(
      email: email,
      username: username,
      accessToken: res.data!['access'],
      refreshToken: res.data!['refresh'],
      rememberMe: rememberMe,
    );
  }

  static Future<void> postRecord(
    BuildContext context, {
    required double glucose,
    double? carbohydrate,
    double? exercise,
    double? insulin,
  }) async {
    await _dio.post(
      '/records/',
      data: {
        'blood_glucose': glucose,
        'carbohydrate_intake': carbohydrate,
        'exercise_duration': exercise,
        'insulin_injection': insulin,
      },
      options: Options(extra: {'context': context}),
    );
  }
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this.dio, this.getAccessToken);

  final Dio dio;
  final String Function() getAccessToken;
  final _nonAuthPaths = const ['/register/', '/token/', '/token/refresh/'];

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (!_nonAuthPaths.contains(options.path)) {
      options.headers['Authorization'] = 'Bearer ${getAccessToken()}';
    }

    super.onRequest(options, handler);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    Future<void> retry() async {
      handler.resolve(await dio.fetch(err.requestOptions));
    }

    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        {
          final context = err.requestOptions.extra['context'] as BuildContext;
          if (!context.mounted) break;

          final nav = await _TimeoutDialog.show(context, err.type);
          switch (nav) {
            case _TimeoutDialogNav.retry:
              await retry();
              return;

            default:
              break;
          }
          break;
        }

      case DioExceptionType.badResponse:
        {
          if (err.response?.statusCode == 401) {
            await Request.refresh();
            await retry();
            return;
          }
          break;
        }

      default:
        break;
    }

    super.onError(err, handler);
  }
}

/* */
/* */
/* */

class CancelConnectionException implements Exception {}

enum _DisconnectedDialogNav { ok }

class _DisconnectedDialog extends StatelessWidget {
  const _DisconnectedDialog._();

  static Future<dynamic> show(BuildContext context) async {
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
  final DioExceptionType type;

  static Future<dynamic> show(
    BuildContext context,
    DioExceptionType type,
  ) async {
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
          Text(type.toString()),
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
