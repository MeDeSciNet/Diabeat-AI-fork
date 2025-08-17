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
              child: CircularProgressIndicator(year2023: false),
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
            Icon(Icons.sms_failed_rounded, size: 100, color: Colors.redAccent),
            _predictionText('連線失敗'),
          ],
        ),
      ),
      false => Column(
        children: [
          Row(
            children: PredictDiabetesFields.prediction
                ? [
                    Icon(
                      Icons.warning_rounded,
                      size: 100,
                      color: Colors.amberAccent,
                    ),
                    Expanded(child: _predictionText('建議追蹤')),
                  ]
                : [
                    Icon(Icons.warning_rounded, size: 100, color: Colors.green),
                    Expanded(child: _predictionText('狀況良好')),
                  ],
          ),
          const SizedBox(height: 20),
          Card.outlined(
            child: ListTile(
              title: const Text('基本資料'),
              subtitle: Table(
                columnWidths: const {
                  0: IntrinsicColumnWidth(),
                  1: IntrinsicColumnWidth(),
                  2: FlexColumnWidth(),
                },
                children: [
                  TableRow(
                    children: [
                      util.paddingText('性別'),
                      util.paddingText(PredictDiabetesFields.genderText),
                      const SizedBox(),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('年齡'),
                      util.paddingText(PredictDiabetesFields.age.toString()),
                      const Text('歲'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('身高'),
                      util.paddingText(PredictDiabetesFields.height.toString()),
                      const Text('cm'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('體重'),
                      util.paddingText(PredictDiabetesFields.weight.toString()),
                      const Text('kg'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('BMI'),
                      util.paddingText(PredictDiabetesFields.bmi.toString()),
                      const Text('kg/m^2'),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          Card.outlined(
            child: ListTile(
              title: const Text('疾病史 / 吸菸史'),
              subtitle: Table(
                columnWidths: const {
                  0: IntrinsicColumnWidth(),
                  1: FlexColumnWidth(),
                },
                children: [
                  TableRow(
                    children: [
                      util.paddingText('高血壓'),
                      PredictDiabetesFields.hypertension
                          ? const Text('有')
                          : const Text('無'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('心臟病'),
                      PredictDiabetesFields.heartDisease
                          ? const Text('有')
                          : const Text('無'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('吸菸史'),
                      Text(PredictDiabetesFields.smokingHistoryText),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          Card.outlined(
            child: ListTile(
              title: const Text('血糖值 / 糖化血色素'),
              subtitle: Table(
                columnWidths: const {
                  0: IntrinsicColumnWidth(),
                  1: IntrinsicColumnWidth(),
                  2: FlexColumnWidth(),
                },
                children: [
                  TableRow(
                    children: [
                      util.paddingText('血糖值'),
                      util.paddingText(
                        PredictDiabetesFields.glucose.toString(),
                      ),
                      const Text('mg/dL'),
                    ],
                  ),
                  TableRow(
                    children: [
                      util.paddingText('糖化血色素'),
                      util.paddingText(PredictDiabetesFields.hba1c.toString()),
                      const Text('%'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    };
  }

  Widget _predictionText(String text) {
    return Text(
      text,
      textAlign: TextAlign.center,
      style: TextStyle(fontSize: 30),
    );
  }
}
