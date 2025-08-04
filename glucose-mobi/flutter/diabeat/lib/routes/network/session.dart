import 'dart:async';
import 'dart:convert';
import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/dialog/ghost_account_dialog.dart';
import 'package:diabeat/routes/network/dialog/timeout_dialog.dart';
import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

({String username, String accessToken, String refreshToken})? _session;

bool get loggedIn => _session != null;
String get username => _session!.username;
String get accessToken => _session!.accessToken;
String get refreshToken => _session!.refreshToken;

void save({
  required String username,
  required String accessToken,
  required String refreshToken,
}) {
  _session = (
    username: username,
    accessToken: accessToken,
    refreshToken: refreshToken,
  );
  prefs.writeRefreshToken(refreshToken);
}

void delete() {
  _session = null;
  prefs.deleteRefreshToken();
}

Future<bool> _rawRefresh(BuildContext context, String oldRefreshToken) async {
  final res = await http
      .post(
        connection.makeUrl('/api/token/refresh/'),
        body: {'refresh': oldRefreshToken},
      )
      .timeout(const Duration(seconds: 3));
  final status = res.statusCode;

  if (200 <= status && status < 300) {
    final data = jsonDecode(res.body);
    save(
      username: data['username'],
      accessToken: data['access'],
      refreshToken: data['refresh'],
    );
    return true;
  }

  if (context.mounted) {
    GhostAccountDialog.show(context);
  }
  return false;
}

Future<bool> tryAuthorize(BuildContext context) async {
  if (loggedIn) {
    return true;
  }

  final oldRefreshToken = await prefs.readRefreshToken();
  while (true) {
    try {
      return context.mounted && await _rawRefresh(context, oldRefreshToken);
      //
    } on TimeoutException {
      if (!context.mounted || await TimeoutDialog.show(context) == null) {
        return false;
      }
    }
  }
}

Future<bool> tryRefresh(BuildContext context) {
  return _rawRefresh(context, refreshToken);
}
