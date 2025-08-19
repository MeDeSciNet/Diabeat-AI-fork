import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page3 extends StatefulWidget {
  const Page3({super.key});

  @override
  State<Page3> createState() => Page3State();
}

class Page3State extends State<Page3> {
  bool? waiting = true;

  @override
  Widget build(BuildContext context) {
    return switch (waiting) {
      true => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Transform.scale(
              scale: 2,
              child: const CircularProgressIndicator(year2023: false),
            ),
            const SizedBox(height: 40),
            _predictionText('檢測中'),
          ],
        ),
      ),
      null => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.sms_failed_rounded,
              size: 100,
              color: Colors.redAccent,
            ),
            _predictionText('連線失敗'),
          ],
        ),
      ),
      false => Column(
        children: [
          Row(
            children: PredictDiabetesFields.prediction
                ? [
                    const Icon(
                      Icons.warning_rounded,
                      size: 100,
                      color: Colors.amberAccent,
                    ),
                    Expanded(child: _predictionText('建議追蹤')),
                  ]
                : [
                    const Icon(
                      Icons.check_circle_rounded,
                      size: 100,
                      color: Colors.green,
                    ),
                    Expanded(child: _predictionText('狀況良好')),
                  ],
          ),
          const SizedBox(height: 20),
          util.figureCard('基本資料', [
            ('性別', PredictDiabetesFields.genderText, null),
            ('年齡', PredictDiabetesFields.age, '歲'),
            ('身高', PredictDiabetesFields.height, 'cm'),
            ('體重', PredictDiabetesFields.weight, 'kg'),
            ('BMI', PredictDiabetesFields.bmi, 'kg/m^2'),
          ]),
          const SizedBox(height: 10),
          util.figureCard('疾病史 / 吸菸史', [
            ('高血壓', PredictDiabetesFields.hypertension ? '有' : '無', null),
            ('心臟病', PredictDiabetesFields.heartDisease ? '有' : '無', null),
            ('吸菸史', PredictDiabetesFields.smokingHistoryText, null),
          ]),
          const SizedBox(height: 10),
          util.figureCard('血糖值 / 糖化血色素', [
            ('血糖值', PredictDiabetesFields.glucose, 'mg/dL'),
            ('糖化血色素', PredictDiabetesFields.hba1c, '%'),
          ]),
        ],
      ),
    };
  }

  Widget _predictionText(String text) {
    return Text(
      text,
      textAlign: TextAlign.center,
      style: const TextStyle(fontSize: 30),
    );
  }
}
