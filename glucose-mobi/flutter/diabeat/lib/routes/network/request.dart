import 'dart:async';
import 'dart:convert';
import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/result.dart';
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/routes/network/dialog/timeout_dialog.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

enum _Method { post, get }

Future<Result> _request(
  BuildContext context,
  _Method method,
  String path, {
  Map<String, dynamic>? body,
  bool auth = false,
  int timeout = 3,
}) async {
  // step 1 : connect
  if (!await connection.tryConnect(context)) {
    return Result.failed();
  }

  // step 2 : make headers & body
  final url = connection.makeUrl(path);
  final headers = {'Content-Type': 'application/json'};
  if (auth) {
    if (!context.mounted || !await session.tryAuthorize(context)) {
      return Result.failed();
    }
    headers['Authorization'] = 'Bearer ${session.accessToken}';
  }
  final stringBody = jsonEncode(body);
  final duration = Duration(seconds: timeout);
  final send = switch (method) {
    _Method.post =>
      () =>
          http.post(url, headers: headers, body: stringBody).timeout(duration),

    _Method.get => () => http.get(url, headers: headers).timeout(duration),
  };

  // step 3 : send & retry request
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
        if (!context.mounted || !await session.tryRefresh(context)) {
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

  assert(false, '[!] escape jail');
  return Result.failed();
}

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
