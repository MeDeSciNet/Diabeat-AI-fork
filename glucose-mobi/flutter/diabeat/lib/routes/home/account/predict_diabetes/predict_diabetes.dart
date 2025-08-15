import 'package:diabeat/routes/home/account/predict_diabetes/page0.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page1.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page2.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page3.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class PredictDiabetesRoot extends StatefulWidget {
  const PredictDiabetesRoot({super.key});

  @override
  State<PredictDiabetesRoot> createState() => _PredictDiabetesRootState();
}

class _PredictDiabetesRootState extends State<PredictDiabetesRoot> {
  final _page0Key = GlobalKey<Page0State>();
  final _page1Key = GlobalKey<Page1State>();
  final _page2Key = GlobalKey<Page2State>();
  final _page3Key = GlobalKey<Page3State>();
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        title: const Text('預測糖尿病'),
        centerTitle: true,
        actions: _index == 3 ? [util.shareIconButton(context)] : null,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: IndexedStack(
          index: _index,
          children: [
            Page0(key: _page0Key, goNextPage: goNextPage),
            Page1(
              key: _page1Key,
              goPrevPage: goPrevPage,
              goNextPage: goNextPage,
            ),
            Page2(
              key: _page2Key,
              goPrevPage: goPrevPage,
              goSendPage: goSendPage,
            ),
            Page3(key: _page3Key),
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
      final p0 = _page0Key.currentState!;
      final gender = p0.gender!;
      final age = p0.age!;
      final heightInMeter = p0.height! / 100;
      final weight = p0.weight!;
      final bmi = weight / (heightInMeter * heightInMeter);

      final p1 = _page1Key.currentState!;
      final hypertension = p1.hypertension;
      final heartDisease = p1.heartDisease;
      final smokingHistory = p1.smokingHistory!;

      final p2 = _page2Key.currentState!;
      final glucose = p2.glucose!;
      final hba1c = p2.hba1c!;

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
      if(!mounted) return;

      if (result.ok) {
        final predcition = result.data['prediction'] == 1;
        _page3Key.currentState!.update(predcition);
      } else {
        // result.failed
      }
    }();
  }
}
