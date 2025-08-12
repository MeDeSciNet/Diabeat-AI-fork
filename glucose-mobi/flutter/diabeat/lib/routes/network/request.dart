import 'dart:async';
import 'dart:convert';
import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/dialog/disconnected_dialog.dart';
import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:diabeat/routes/network/dialog/refresh_failed_dialog.dart';
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/routes/network/dialog/timeout.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

Future<bool> _tryConnect(BuildContext context) async {
  if (connection.existAddr) {
    return true;
  }

  if (await prefs.existAddr()) {
    connection.connectTo(await prefs.readAddr());
    return true;
  }

  return context.mounted && await DisconnectedDialog.show(context) == true;
}

Future<bool> refresh(BuildContext context, String oldRefreshToken) async {
  if (!await _tryConnect(context)) {
    return false;
  }

  final res = await http
      .post(
        connection.makeUrl('/token/refresh'),
        body: {'refresh': oldRefreshToken},
      )
      .timeout(const Duration(seconds: 1));

  final status = res.statusCode;

  if (status == 200) {
    final data = jsonDecode(res.body);
    session.save(
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
    return true;
  }

  if (context.mounted) {
    RefreshFailedDialog.show(context);
  }
  return false;
}

Future<Result> _handle(
  BuildContext context,
  Future<(int, String)> Function() request,
) async {
  if (!await _tryConnect(context)) {
    return Result.failed();
  }

  bool retry;
  do {
    retry = false;

    try {
      final (statusCode, body) = await request();

      if (200 <= statusCode && statusCode < 300) {
        return Result.successful(body);
      } else if (statusCode == 401) {
        if (!context.mounted || !await refresh(context, session.refreshToken)) {
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
        case true:
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
}) {
  return _handle(context, () async {
    final res = await http
        .post(
          connection.makeUrl('/token'),
          body: {'username_or_email': email, 'password': password},
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });
}

Future<Result> register(
  BuildContext context, {
  required String email,
  required String username,
  required String password,
}) {
  return _handle(context, () async {
    final res = await http
        .post(
          connection.makeUrl('/register'),
          body: {'email': email, 'username': username, 'password': password},
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });
}

Future<Result> postRecord(
  BuildContext context, {
  required double glucose,
  double? carbohydrate,
  double? exercise,
  double? insulin,
}) {
  return _handle(context, () async {
    final res = await http
        .post(
          connection.makeUrl('/records'),
          headers: _configHeaders(null, json: true, auth: true),
          body: jsonEncode({
            'blood_glucose': glucose,
            'carbohydrate_intake': carbohydrate,
            'exercise_duration': exercise,
            'insulin_injection': insulin,
          }),
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });
}

Future<Result> getRecords(BuildContext context) {
  return _handle(context, () async {
    final res = await http.get(
      connection.makeUrl('/records'),
      headers: _configHeaders(null, auth: true),
    );

    return (res.statusCode, res.body);
  });
}

Future<Result> predictCarbohydrate(BuildContext context, XFile xFile) {
  return _handle(context, () async {
    final request = http.MultipartRequest(
      'POST',
      connection.makeUrl('/predict'),
    );

    _configHeaders(request.headers, auth: true);

    request.files.add(
      http.MultipartFile(
        'image',
        xFile.openRead(),
        await xFile.length(),
        filename: xFile.name,
      ),
    );

    final res = await request.send();
    return (res.statusCode, await res.stream.bytesToString());
  });
}

Future<Result> predictDiabetes(
  BuildContext context, {
  required String gender,
  required int age,
  required double bmi,
  required bool hypertension,
  required bool heartDisease,
  required String smokingHistory,
  required double glucose,
  required double hba1c,
}) {
  return _handle(context, () async {
    final res = await http
        .post(
          connection.makeUrl('/predictform'),
          headers: _configHeaders(null, json: true, auth: true),
          body: jsonEncode({
            'gender': gender,
            'age': age,
            'bmi': bmi,
            'hypertension': hypertension,
            'heart_disease': heartDisease,
            'smoking_history': smokingHistory,
            'HbA1c_level': hba1c,
            'blood_glucose_level': glucose,
          }),
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });
}

/* */
/* */
/* */

Map<String, String> _configHeaders(
  Map<String, String>? origin, {
  bool json = false,
  bool auth = false,
}) {
  origin ??= {};
  if (json) {
    origin['Content-Type'] = 'application/json';
  }
  if (auth) {
    origin['Authorization'] = 'Bearer ${session.accessToken}';
  }
  return origin;
}

class Result {
  Result._(this.ok, [String? body])
    : data = body == null ? null : jsonDecode(body);

  Result.successful([String? body]) : this._(true, body);
  Result.failed([String? body]) : this._(false, body);

  final bool ok;
  final dynamic data;
}
