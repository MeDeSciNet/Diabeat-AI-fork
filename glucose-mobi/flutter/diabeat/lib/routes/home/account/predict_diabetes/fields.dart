class PredictDiabetesFields {
  const PredictDiabetesFields._();

  // page 0
  static late String gender;
  static late int age;
  static late double height;
  static late double weight;
  static late double bmi;
  static String get genderText => gender == 'male' ? '男' : '女';

  // page 1
  static bool hypertension = false;
  static bool heartDisease = false;
  static late String smokingHistory;
  static final smokingHistoryMap = const {
    'never': '從不吸菸',
    'former': '曾經吸菸 (已戒菸)',
    'not current': '目前未吸菸',
    'current': '目前有吸菸',
  };
  static String get smokingHistoryText => smokingHistoryMap[smokingHistory]!;

  // page 2
  static late double glucose;
  static late double hba1c;

  // page 3
  static late bool prediction;
}
