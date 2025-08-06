import 'package:flutter/material.dart';

class PredictDiabetesPage extends StatefulWidget {
  const PredictDiabetesPage({super.key});

  @override
  State<PredictDiabetesPage> createState() => _PredictDiabetesPageState();
}

class _PredictDiabetesPageState extends State<PredictDiabetesPage> {
  String? _gender;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('預測是否有糖尿病', style: const TextStyle(fontSize: 55)),
          const SizedBox(height: 20),
          RadioListTile<String>(
            title: const Text('男'),
            value: 'male',
            groupValue: _gender,
            onChanged: (value) {
              setState(() => _gender = value);
            },
          ),
          RadioListTile<String>(
            title: const Text('女'),
            value: 'female',
            groupValue: _gender,
            onChanged: (value) {
              setState(() => _gender = value);
            },
          ),
        ],
      ),
    );
  }
}
