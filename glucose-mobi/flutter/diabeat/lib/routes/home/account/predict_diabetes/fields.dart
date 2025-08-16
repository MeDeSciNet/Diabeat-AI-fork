class PredictDiabetesField {
  static final _instance = PredictDiabetesField._();

  PredictDiabetesField._();
  factory PredictDiabetesField() {
    return _instance;
  }

  // page 0
  String? gender;
  int? age;
  double? height;
  double? weight;

  // page 1
  bool hypertension = false;
  bool heartDisease = false;
  String? smokingHistory;

  // page 2
  double? glucose;
  double? hba1c;

  // page 3
  bool? prediction;
}
