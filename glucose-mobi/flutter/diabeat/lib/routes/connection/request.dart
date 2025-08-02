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

  static Future<bool> init() async {
    _dio.interceptors.add(_AuthInterceptor(_dio, () => _session!.accessToken));

    final addr = await Prefs.getAddr();
    if (addr == null) {
      return false;
    }
    _dio.options.baseUrl = 'http://$addr:8000/api';

    final oldRefreshToken = await Prefs.getEncryptedRefreshToken();
    if (oldRefreshToken == null) {
      return false;
    }

    try {
      await refresh();
      return true;
    } on DioException {
      return false;
    }
  }

  static void _saveSession({
    required String username,
    required String accessToken,
    required String refreshToken,
  }) {
    _session = (
      username: username,
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
    Prefs.writeEncryptedRefreshToken(refreshToken);
  }

  static void deleteSession() {
    _session = null;
    Prefs.delEncryptedRefreshToken();
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

  static void saveConnection(String value) {
    _dio.options.baseUrl = 'http://$value:8000/api';
    Prefs.writeAddr(value);
  }

  /* */
  /* */
  /* ===== request ===== */

  static Options _makeTimeoutOpt(BuildContext context) {
    return Options(
      extra: {
        'when_timeout': () async {
          // return <dynamic>

          if (!context.mounted) return null;
          return await _TimeoutDialog.show(context);
        },
      },
    );
  }

  static Future<void> refresh([BuildContext? context]) async {
    Options? opt;
    String oldRefreshToken;

    if (_session == null) {
      opt = _makeTimeoutOpt(context!);
      oldRefreshToken = (await Prefs.getEncryptedRefreshToken())!;
    } else {
      assert(context != null, 'You should not pass context here !');
      oldRefreshToken = _session!.refreshToken;
    }

    final res = await _dio.post<JsonMap>(
      '/token/refresh/',
      data: {'refresh': oldRefreshToken},
      options: opt,
    );
    final data = res.data!;

    _saveSession(
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
  }

  static Future<void> logIn(
    BuildContext context, {
    required String email,
    required String password,
  }) async {
    final extraOpt = _makeTimeoutOpt(context);
    await _tryConnect(context);

    final res = await _dio.post<JsonMap>(
      '/token/',
      data: {'username_or_email': email, 'password': password},
      options: extraOpt,
    );
    final data = res.data!;

    _saveSession(
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
  }

  static Future<void> register(
    BuildContext context, {
    required String email,
    required String username,
    required String password,
  }) async {
    final extraOpt = _makeTimeoutOpt(context);
    await _tryConnect(context);

    final res = await _dio.post<JsonMap>(
      '/register/',
      data: {'email': email, 'username': username, 'password': password},
      options: extraOpt,
    );
    final data = res.data!;

    _saveSession(
      username: username,
      accessToken: data['access'],
      refreshToken: data['refresh'],
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
      options: _makeTimeoutOpt(context),
    );
  }

  static Future<double> predictCarbohydrate(BuildContext context) async {
    // final formData = FormData.fromMap({
    //   'image': MultipartFile.fromFile(filePath),
    // });

    final formData = null;

    final res = await _dio.post<JsonMap>(
      '/predict/',
      data: formData,
      options: _makeTimeoutOpt(context),
    );

    return double.parse(res.data!['predicted_value']);
  }
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor(this.dio, this.getAccessToken);

  final Dio dio;
  final String Function() getAccessToken;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final nonAuthPaths = const ['/register/', '/token/', '/token/refresh/'];
    if (!nonAuthPaths.contains(options.path)) {
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
          final action =
              err.requestOptions.extra['when_timeout']
                  as Future<dynamic> Function()?;

          switch (await action?.call()) {
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


/* */
/* */
/* */

