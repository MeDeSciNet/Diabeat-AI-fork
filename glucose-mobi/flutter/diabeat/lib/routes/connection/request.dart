import 'dart:async';
import 'dart:convert';
import 'package:diabeat/routes/connection/connection.dart' as connection;
import 'package:diabeat/routes/connection/session.dart' as session;
import 'package:diabeat/routes/connection/timeout_dialog.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

Future<Result> _request(
  BuildContext context,
  _Method method,
  String path, {
  Map<String, dynamic>? body,
  bool auth = false,
  int timeout = 3,
}) async {
  if (!await connection.connect(context)) {
    return Result.failed();
  }

  final url = connection.makeUrl(path);

  final Map<String, String>? headers;
  if (auth && session.loggedIn) {
    headers = {'Authorization': session.accessToken};
  } else {
    headers = null;
  }

  final duration = Duration(seconds: timeout);
  final send = switch (method) {
    _Method.post =>
      () => http.post(url, headers: headers, body: body).timeout(duration),
    _Method.get => () => http.get(url, headers: headers).timeout(duration),
  };

  bool retry;
  do {
    retry = false;

    try {
      final res = await send();
      final status = res.statusCode;
      final body = res.body;

      if (200 <= status && status < 300) {
        return Result.successful(body);
      } else if (status == 401) {
        if (!await _refresh()) {
          // refresh failed
          // should not happen !
          assert(false, 'Refresh Failed !');
          return Result.failed();
        }
        retry = true;
      } else {
        return Result.failed(body);
      }
    } on TimeoutException {
      if (!context.mounted) {
        return Result.failed();
      }

      switch (await TimeoutDialog.show(context)) {
        case TimeoutDialogNav.retry:
          retry = true;
          break;

        default:
          return Result.failed();
      }
    }
  } while (retry);

  assert(false, 'should not goto here !');
  return Result.failed();
}

Future<bool> _refresh() async {
  final url = connection.makeUrl('/api/token/refresh/');
  final oldRefreshToken = await session.getRefreshToken();
  final duration = const Duration(seconds: 3);

  try {
    final res = await http
        .post(url, body: {'refresh': oldRefreshToken})
        .timeout(duration);
    final status = res.statusCode;

    if (200 <= status && status < 300) {
      final data = jsonDecode(res.body);
      session.save(
        username: data['username'],
        accessToken: data['access'],
        refreshToken: data['refresh'],
      );
      return true;
    }

    return false;
  } on TimeoutException {
    return false;
  }
}

/* */
/* */
/* */

Future<Result> logIn(
  BuildContext context, {
  required String email,
  required String password,
}) async {
  final result = await _request(
    context,
    _Method.post,
    '/api/token/',
    body: {'username_or_email': email, 'password': password},
  );

  if (result.ok) {
    final data = result.data;
    session.save(
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
  }

  return result;
}

Future<Result> register(
  BuildContext context, {
  required String email,
  required String username,
  required String password,
}) async {
  final result = await _request(
    context,
    _Method.post,
    '/api/register/',
    body: {'email': email, 'username': username, 'password': password},
  );

  if (result.ok) {
    final data = result.data;
    session.save(
      username: username,
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
  }

  return result;
}

Future<Result> postRecord(
  BuildContext context, {
  required double glucose,
  double? carbohydrate,
  double? exercise,
  double? insulin,
}) async {
  return await _request(
    context,
    _Method.post,
    '/api/records/',
    body: {
      'blood_glucose': glucose,
      'carbohydrate_intake': carbohydrate,
      'exercise_duration': exercise,
      'insulin_injection': insulin,
    },
    auth: true,
  );
}

Future<Result> predictCarbohydrate(BuildContext context) async {
  // TODO
  return await _request(context, _Method.post, '/api/predict/', auth: true);
}

/* */
/* */
/* */

class Result {
  Result._(this.ok, [String? body])
    : data = body == null ? null : jsonDecode(body);

  Result.successful([String? body]) : this._(true, body);
  Result.failed([String? body]) : this._(false, body);

  final bool ok;
  final dynamic data;
}

enum _Method { post, get }
