import 'dart:convert';

class Result {
  Result._(this.ok, [String? body])
    : data = body == null ? null : jsonDecode(body);

  Result.successful([String? body]) : this._(true, body);
  Result.failed([String? body]) : this._(false, body);

  final bool ok;
  final dynamic data;
}
