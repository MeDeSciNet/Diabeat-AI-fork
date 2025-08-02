import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Result> _request(_Method method, String path) async {}

Future<Result> logIn() async {}

class Result {
  Result._(this.ok, [String? body])
    : data = body == null ? null : jsonDecode(body);

  Result.successful([String? body]) : this._(true, body);
  Result.failed([String? body]) : this._(false, body);

  final bool ok;
  final dynamic data;
}

enum _Method { post, get }
