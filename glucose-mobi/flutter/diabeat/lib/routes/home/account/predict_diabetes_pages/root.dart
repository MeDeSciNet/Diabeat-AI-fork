import 'package:diabeat/routes/home/account/predict_diabetes_pages/blood_figure_page.dart';
import 'package:diabeat/routes/home/account/predict_diabetes_pages/medical_history_page.dart';
import 'package:diabeat/routes/home/account/predict_diabetes_pages/personal_info_page.dart';
import 'package:diabeat/routes/home/account/predict_diabetes_pages/result_page.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:flutter/material.dart';

class PredictDiabetesPage extends StatefulWidget {
  const PredictDiabetesPage({super.key});

  @override
  State<PredictDiabetesPage> createState() => _PredictDiabetesPageState();
}

class _PredictDiabetesPageState extends State<PredictDiabetesPage> {
  final _pageKeys = [
    GlobalKey<PersonalInfoPageState>(),
    GlobalKey<MedicalHistoryPageState>(),
    GlobalKey<BloodFigurePageState>(),
    GlobalKey<ResultPageState>(),
  ];
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: const Icon(Icons.arrow_back_ios_new),
        ),
        title: const Text('預測糖尿病'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: IndexedStack(
          index: _index,
          children: [
            PersonalInfoPage(key: _pageKeys[0], goNextPage: goNextPage),
            MedicalHistoryPage(
              key: _pageKeys[1],
              goPrevPage: goPrevPage,
              goNextPage: goNextPage,
            ),
            BloodFigurePage(
              key: _pageKeys[2],
              goPrevPage: goPrevPage,
              goSendPage: goSendPage,
            ),
            ResultPage(key: _pageKeys[3]),
          ],
        ),
      ),
    );
  }

  void goPrevPage() {
    setState(() => _index--);
  }

  void goNextPage() {
    setState(() => _index++);
  }

  void goSendPage() {
    setState(() => _index = 3);
    () async {
      final page0State = _pageKeys[0].currentState! as PersonalInfoPageState;
      final gender = page0State.gender!;
      final age = page0State.age!;
      final heightInMeter = page0State.height! / 100;
      final weight = page0State.weight!;
      final bmi = weight / (heightInMeter * heightInMeter);

      final page1State = _pageKeys[1].currentState! as MedicalHistoryPageState;
      final hypertension = page1State.hypertension;
      final heartDisease = page1State.heartDisease;
      final smokingHistory = page1State.smokingHistory!;

      final page2State = _pageKeys[2].currentState! as BloodFigurePageState;
      final glucose = page2State.glucose!;
      final hba1c = page2State.hba1c!;

      final result = await request.predictDiabetes(
        context,
        gender: gender,
        age: age,
        bmi: bmi,
        hypertension: hypertension,
        heartDisease: heartDisease,
        smokingHistory: smokingHistory,
        glucose: glucose,
        hba1c: hba1c,
      );

      if (result.ok) {
        final predcition = result.dataAsMap['prediction'] == 1;
        final page3State = _pageKeys[3].currentState! as ResultPageState;
        page3State.setState(() => page3State.prediction = predcition);
      } else {
        // result.failed
      }
    }();
  }
}
