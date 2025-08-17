import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page0.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page1.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page2.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/page3.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

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

  GlobalKey<FormState> get _thisFormKey => _formKeys[_index];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        title: const Text('AI 糖尿病風險檢測'),
        centerTitle: true,
        actions: [
          if (_index == 3 && _page3Key.currentState!.waiting == false)
            IconButton(
              onPressed: _share,
              icon: const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 30),
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
                  Page1(),
                  const Spacer(),
                  Row(
                    children: [
                      _prevPageButton(),
                      const SizedBox(width: 20),
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
                      const SizedBox(width: 20),
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
          util.formUnfocus(_thisFormKey);
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
          if (_thisFormKey.currentState!.validate()) {
            _thisFormKey.currentState!.save();
            util.formUnfocus(_thisFormKey);
            setState(() => _index++);
          }
        },
        style: util.filledPageButtonStyle(),
        icon: const Icon(Icons.arrow_forward_rounded),
        iconAlignment: IconAlignment.end,
        label: const Text('下一頁'),
      ),
    );
  }

  Widget _sendButton() {
    return Expanded(
      child: FilledButton.icon(
        onPressed: () async {
          if (!_thisFormKey.currentState!.validate()) return;
          _thisFormKey.currentState!.save();
          util.formUnfocus(_thisFormKey);
          setState(() => _index++);

          final heightInMeter = PredictDiabetesFields.height! / 100;
          final bmi =
              PredictDiabetesFields.weight! / (heightInMeter * heightInMeter);

          PredictDiabetesFields.bmi = double.parse(bmi.toStringAsFixed(1));

          final (ok, data) = await request.predictDiabetes(
            context,
            gender: PredictDiabetesFields.gender!,
            age: PredictDiabetesFields.age!,
            bmi: PredictDiabetesFields.bmi!,
            hypertension: PredictDiabetesFields.hypertension,
            heartDisease: PredictDiabetesFields.heartDisease,
            smokingHistory: PredictDiabetesFields.smokingHistory!,
            glucose: PredictDiabetesFields.glucose!,
            hba1c: PredictDiabetesFields.hba1c!,
          );
          if (!_page3Key.currentState!.mounted) return;

          if (ok) {
            _page3Key.currentState!.setState(() {
              _page3Key.currentState!.waiting = false;
              PredictDiabetesFields.prediction = data['prediction'] == 1;
            });
          } else {
            _page3Key.currentState!.setState(() {
              _page3Key.currentState!.waiting = null;
            });
          }
        },
        style: util.filledPageButtonStyle(),
        iconAlignment: IconAlignment.end,
        icon: const Icon(Icons.send_rounded),
        label: const Text('送出'),
      ),
    );
  }

  void _share() {
    final text =
        '''
[[ Diabeat - AI糖尿病風險檢測 ]]

[基本資料]
性別: ${PredictDiabetesFields.genderText}
年齡: ${PredictDiabetesFields.age} 歲
身高: ${PredictDiabetesFields.height} cm
體重: ${PredictDiabetesFields.weight} kg
BMI: ${PredictDiabetesFields.bmi} kg/m^2

[疾病史/吸菸史]
高血壓: ${PredictDiabetesFields.hypertension ? '有' : '無'}
心臟病: ${PredictDiabetesFields.heartDisease ? '有' : '無'}
吸菸史: ${PredictDiabetesFields.smokingHistoryText}

[血糖值/糖化血色素]
血糖值: ${PredictDiabetesFields.glucose} mg/dL
糖化血色素: ${PredictDiabetesFields.hba1c} %

[檢測結果]
${PredictDiabetesFields.prediction ? '有' : '無'}
''';

    SharePlus.instance.share(ShareParams(text: text));
  }
}
