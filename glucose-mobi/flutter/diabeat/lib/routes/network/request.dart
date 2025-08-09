import 'dart:async';
import 'dart:convert';
import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/routes/network/dialog/timeout_dialog.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

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

Future<Result> _handle(
  BuildContext context,
  bool auth,
  Future<(int, String)> Function() request,
) async {
  if (!await connection.tryConnect(context)) {
    return Result.failed();
  }

  if (auth) {
    if (!context.mounted || !await session.tryAuthorize(context)) {
      return Result.failed();
    }
  }

  bool retry;
  do {
    retry = false;

    try {
      final (statusCode, body) = await request();

      if (200 <= statusCode && statusCode < 300) {
        return Result.successful(body);
      } else if (statusCode == 401) {
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
}) async {
  final result = await _handle(context, false, () async {
    final res = await http
        .post(
          connection.makeUrl('/token'),
          body: {'username_or_email': email, 'password': password},
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });

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
  final result = await _handle(context, false, () async {
    final res = await http
        .post(
          connection.makeUrl('/register'),
          body: {'email': email, 'username': username, 'password': password},
        )
        .timeout(const Duration(seconds: 3));

    return (res.statusCode, res.body);
  });

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
  return await _handle(context, true, () async {
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

Future<Result> getRecords(BuildContext context) async {
  return await _handle(context, true, () async {
    final res = await http.get(
      connection.makeUrl('/records'),
      headers: _configHeaders(null, auth: true),
    );

    return (res.statusCode, res.body);
  });
}

Future<Result> predictCarbohydrate(BuildContext context, XFile xFile) async {
  return await _handle(context, true, () async {
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
  bool get haveData => data != null;
  Map<String, dynamic> get dataAsMap => data;
  List<Map<String, dynamic>> get dataAsList =>
      (data as List).cast<Map<String, dynamic>>();
}
