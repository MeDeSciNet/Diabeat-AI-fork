import 'dart:async';
import 'dart:convert';
import 'package:diabeat/network/connection.dart' as connection;
import 'package:diabeat/routes/dialog/disconnected_dialog.dart';
import 'package:diabeat/routes/dialog/refresh_failed_dialog.dart';
import 'package:diabeat/network/session.dart' as session;
import 'package:diabeat/routes/dialog/timeout_dialog.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

Future<(bool, dynamic)> logIn(
  BuildContext context, {
  required String email,
  required String password,
}) async {
  if (!await _connect(context) || !context.mounted) {
    return (false, null);
  }

  return _handle(context, () async {
    final res = await _timeout(
      http.post(
        connection.makeUrl('/token'),
        body: {'username_or_email': email, 'password': password},
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> register(
  BuildContext context, {
  required String email,
  required String username,
  required String password,
}) async {
  if (!await _connect(context) || !context.mounted) {
    return (false, null);
  }

  return _handle(context, () async {
    final res = await _timeout(
      http.post(
        connection.makeUrl('/register'),
        body: {'email': email, 'username': username, 'password': password},
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> postRecord(
  BuildContext context, {
  required double glucose,
  double? carbohydrate,
  double? exercise,
  double? insulin,
}) {
  return _handle(context, () async {
    final res = await _timeout(
      http.post(
        connection.makeUrl('/records'),
        headers: _configHeaders({}, auth: true, json: true),
        body: jsonEncode({
          'blood_glucose': glucose,
          'carbohydrate_intake': carbohydrate,
          'exercise_duration': exercise,
          'insulin_injection': insulin,
        }),
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> getRecords(BuildContext context) {
  return _handle(context, () async {
    final res = await _timeout(
      http.get(
        connection.makeUrl('/records'),
        headers: _configHeaders({}, auth: true),
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> predictCarbs(BuildContext context, XFile xFile) {
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

    final res = await _timeout(request.send());
    return (res.statusCode, await res.stream.bytesToString());
  });
}

Future<(bool, dynamic)> predictDiabetes(
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
    final res = await _timeout(
      http.post(
        connection.makeUrl('/predictform'),
        headers: _configHeaders({}, auth: true, json: true),
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
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> consult(BuildContext context) {
  return _handle(context, () async {
    final res = await http.get(
      connection.makeUrl('/chat'),
      headers: _configHeaders({}, auth: true),
    );

    return (res.statusCode, res.body);
  }, refreshFirst: true);
}

Future<(bool, dynamic)> getInfo(BuildContext context) {
  return _handle(context, () async {
    final res = await _timeout(
      http.get(
        connection.makeUrl('/info/get'),
        headers: _configHeaders({}, auth: true),
      ),
    );

    return (res.statusCode, res.body);
  });
}

Future<(bool, dynamic)> updateInfo(
  BuildContext context, {
  required int age,
  required double height,
  required double weight,
}) {
  return _handle(context, () async {
    final res = await _timeout(
      http.post(
        connection.makeUrl('/info/update'),
        headers: _configHeaders({}, auth: true, json: true),
        body: jsonEncode({'age': age, 'height': height, 'weight': weight}),
      ),
    );

    return (res.statusCode, res.body);
  });
}

/* */
/* */
/* */

Map<String, String> _configHeaders(
  Map<String, String> origin, {
  bool auth = false,
  bool json = false,
}) {
  if (auth) {
    origin['Authorization'] = 'Bearer ${session.accessToken}';
  }
  if (json) {
    origin['Content-Type'] = 'application/json';
  }
  return origin;
}

Future<T> _timeout<T extends http.BaseResponse>(Future<T> future) {
  return future.timeout(const Duration(seconds: 3));
}

/// should only be called in "login" and "register"
Future<bool> _connect(BuildContext context) async {
  return connection.existAddr || await DisconnectedDialog.show(context) == true;
}

/// should only be called in "_handle"
Future<bool> _refresh(BuildContext context) async {
  final res = await _timeout(
    http.post(
      connection.makeUrl('/token/refresh'),
      body: {'refresh': session.refreshToken},
    ),
  );

  if (res.statusCode == 200) {
    final data = jsonDecode(res.body);
    session.save(
      email: session.email,
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

/// arg "refreshFirst" used in "consult"
Future<(bool, dynamic)> _handle(
  BuildContext context,
  Future<(int, String)> Function() request, {
  bool refreshFirst = false,
}) async {
  //
  bool retry;
  do {
    retry = false;

    try {
      if (refreshFirst && !await _refresh(context)) {
        break;
      }

      final (status, body) = await request();

      // 200 ~ 300
      if (200 <= status && status < 300) {
        return (true, jsonDecode(body));
      }

      // 401
      if (status == 401) {
        if (context.mounted && await _refresh(context)) {
          retry = true;
          continue;
        }
        break;
      }

      // others
      return (false, jsonDecode(body));
      //
    } on TimeoutException {
      if (context.mounted && await TimeoutDialog.show(context) == true) {
        retry = true;
        continue;
      }
      break;
    }
  } while (retry);

  // failure sewer
  return (false, null);
}
