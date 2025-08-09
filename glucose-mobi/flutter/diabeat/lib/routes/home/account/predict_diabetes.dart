import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class PredictDiabetesPage extends StatefulWidget {
  const PredictDiabetesPage({super.key});

  @override
  State<PredictDiabetesPage> createState() => _PredictDiabetesPageState();
}

class _PredictDiabetesPageState extends State<PredictDiabetesPage> {
  int _index = 0;
  String? _gender;

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
        padding: EdgeInsets.all(20),
        child: IndexedStack(
          index: _index,
          children: [
            _buildPersonalInfoPage(),
            _buildMedicalHistoryPage(),
            _buildFigurePage(),
          ],
        ),
      ),
    );
  }

  Widget _buildPreviousPageButton() {
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: () {
          setState(() => _index--);
        },
        style: util.outlinedPageButtonStyle(),
        icon: const Icon(Icons.arrow_back_ios_new),
        label: const Text('上一頁'),
      ),
    );
  }

  Widget _buildNextPageButton() {
    return Expanded(
      child: FilledButton.icon(
        onPressed: () {
          setState(() => _index++);
        },
        style: util.filledPageButtonStyle(),
        icon: const Icon(Icons.arrow_forward_ios),
        iconAlignment: IconAlignment.end,
        label: const Text('下一頁'),
      ),
    );
  }

  Widget _buildPersonalInfoPage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('性別', style: TextStyle(fontSize: 25)),
        RadioListTile(
          title: const Text('男'),
          value: 'male',
          groupValue: _gender,
          onChanged: (value) {
            setState(() => _gender = value);
          },
        ),
        RadioListTile(
          title: const Text('女'),
          value: 'female',
          groupValue: _gender,
          onChanged: (value) {
            setState(() => _gender = value);
          },
        ),
        const Spacer(),
        Row(
          children: [
            const Spacer(),
            const SizedBox(width: 10),
            _buildNextPageButton(),
          ],
        ),
      ],
    );
  }

  Widget _buildMedicalHistoryPage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('medical history'),
        const Spacer(),
        Row(
          children: [
            _buildPreviousPageButton(),
            const SizedBox(width: 10),
            _buildNextPageButton(),
          ],
        ),
      ],
    );
  }

  Widget _buildFigurePage() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('figure'),
        const Spacer(),
        Row(
          children: [
            _buildPreviousPageButton(),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                onPressed: () {
                  // send
                },
                style: util.filledPageButtonStyle(),
                icon: const Icon(Icons.send),
                iconAlignment: IconAlignment.end,
                label: const Text('送出'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _MedicalHistoryCheckBox extends StatefulWidget {
  @override
  State<_MedicalHistoryCheckBox> createState() =>
      _MedicalHistoryCheckBoxState();
}

class _MedicalHistoryCheckBoxState extends State<_MedicalHistoryCheckBox> {
  bool hypertension = false;
  bool cvd = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('疾病史', style: TextStyle(fontSize: 20)),
        CheckboxListTile(
          value: hypertension,
          onChanged: (value) {
            setState(() => hypertension = value!);
          },
          title: const Text('高血壓'),
          controlAffinity: ListTileControlAffinity.leading,
        ),
        CheckboxListTile(
          title: const Text('心臟病'),
          value: cvd,
          onChanged: (value) {
            setState(() => cvd = value!);
          },
          controlAffinity: ListTileControlAffinity.leading,
        ),
      ],
    );
  }
}
