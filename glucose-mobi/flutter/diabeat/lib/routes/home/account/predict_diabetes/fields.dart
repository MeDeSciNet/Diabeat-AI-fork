class PredictDiabetesFields {
  const PredictDiabetesFields._();

  // page 0
  static String? gender;
  static int? age;
  static double? height;
  static double? weight;
  static double? bmi;
  static String get genderText => gender == 'male' ? '男' : '女';

  // page 1
  static bool hypertension = false;
  static bool heartDisease = false;
  static String? smokingHistory;
  static final smokingHistoryMap = const {
    'never': '從不吸菸',
    'former': '曾經吸菸 (已戒菸)',
    'not current': '目前未吸菸',
    'current': '目前有吸菸',
  };
  static String get smokingHistoryText => smokingHistoryMap[smokingHistory]!;

  // page 2
  static double? glucose;
  static double? hba1c;

  // page 3
  static late bool prediction;
}
