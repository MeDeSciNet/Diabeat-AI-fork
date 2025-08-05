import 'dart:convert';

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
