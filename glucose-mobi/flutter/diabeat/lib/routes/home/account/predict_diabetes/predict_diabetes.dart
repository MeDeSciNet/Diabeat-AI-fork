import 'dart:developer';
import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
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
  final _formKeys = [
    GlobalKey<FormState>(),
    GlobalKey<FormState>(),
    GlobalKey<FormState>(),
  ];
  final _page3Key = GlobalKey<Page3State>();
  int _index = 0;

  FormState get _formState => _formKeys[_index].currentState!;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        title: const Text('AI 糖尿病風險檢測'),
        centerTitle: true,
        actions: [
          if (_index == 3)
            IconButton(
              onPressed: () {
                // share
              },
              icon: const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: IndexedStack(
          index: _index,
          children: [
            Form(
              key: _formKeys[0],
              child: Column(
                children: [
                  Page0(),
                  const Spacer(),
                  Row(
                    children: [
                      const Spacer(),
                      const SizedBox(width: 20),
                      _nextPageButton(),
                    ],
                  ),
                ],
              ),
            ),
            Form(
              key: _formKeys[1],
              child: Column(
                children: [
                  const Page1(),
                  const Spacer(),
                  Row(
                    children: [
                      _prevPageButton(),
                      const Spacer(),
                      _nextPageButton(),
                    ],
                  ),
                ],
              ),
            ),
            Form(
              key: _formKeys[2],
              child: Column(
                children: [
                  Page2(),
                  const Spacer(),
                  Row(
                    children: [
                      _prevPageButton(),
                      const Spacer(),
                      _sendButton(),
                    ],
                  ),
                ],
              ),
            ),
            Page3(key: _page3Key),
          ],
        ),
      ),
    );
  }

  Widget _prevPageButton() {
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: () {
          setState(() => _index--);
        },
        style: util.outlinedPageButtonStyle(),
        icon: const Icon(Icons.arrow_back_rounded),
        label: const Text('上一頁'),
      ),
    );
  }

  Widget _nextPageButton() {
    return Expanded(
      child: FilledButton.icon(
        onPressed: () {
          if (_formState.validate()) {
            _formState.save();
            setState(() => _index++);
          }
        },
        style: util.filledPageButtonStyle(),
        icon: const Icon(Icons.arrow_forward_rounded),
        label: const Text('下一頁'),
      ),
    );
  }

  Widget _sendButton() {
    return Expanded(
      child: FilledButton.icon(
        onPressed: () async {
          if (!_formState.validate()) return;
          _formState.save();
          setState(() => _index++);

          final heightInMeter = PredictDiabetesField().height! / 100;
          final bmi =
              PredictDiabetesField().weight! / (heightInMeter * heightInMeter);

          final (ok, data) = await request.predictDiabetes(
            context,
            gender: PredictDiabetesField().gender!,
            age: PredictDiabetesField().age!,
            bmi: bmi,
            hypertension: PredictDiabetesField().hypertension,
            heartDisease: PredictDiabetesField().heartDisease,
            smokingHistory: PredictDiabetesField().smokingHistory!,
            glucose: PredictDiabetesField().glucose!,
            hba1c: PredictDiabetesField().hba1c!,
          );
          if (!mounted) return;

          if (ok) {
            _page3Key.currentState!.setState(() {
              PredictDiabetesField().prediction = data['prediction'] == 1;
            });
          } else {
            log('predict diabetes failed');
          }
        },
        style: util.filledPageButtonStyle(),
        icon: const Icon(Icons.send_rounded),
        label: const Text('送出'),
      ),
    );
  }
}
