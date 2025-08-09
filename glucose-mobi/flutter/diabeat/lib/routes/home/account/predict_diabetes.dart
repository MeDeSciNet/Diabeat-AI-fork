import 'dart:developer';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class PredictDiabetesPage extends StatelessWidget {
  PredictDiabetesPage({super.key});
  final _formKey = GlobalKey<FormState>();

  @override
  Widget build(BuildContext context) {
    return Row(
        children: [
          const SizedBox(width: 20),
          Expanded(
            child: FilledButton.tonal(
              onPressed: () {},
              child: const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(height:20,),
                  Icon(Icons.male, size: 50),
                  Text('男', style: TextStyle(fontSize: 30)),
                  SizedBox(height:20,),
                ],
              ),
            ),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: FilledButton.tonal(
              onPressed: () {},
              child: const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(height:20,),
                  Icon(Icons.female, size: 50),
                  Text('女', style: TextStyle(fontSize: 30)),
                  SizedBox(height:20,),
                ],
              ),
            ),
          ),
          const SizedBox(width: 20),
        ],
      );
    // return Scaffold(
    //   appBar: AppBar(
    //     leading: IconButton(
    //       onPressed: () {
    //         Navigator.pop(context);
    //       },
    //       icon: const Icon(Icons.arrow_back_ios_new),
    //     ),
    //     title: const Text('預測糖尿病'),
    //   ),
    //   body: ,
      // body: Form(
      //   key: _formKey,
      //   child: Padding(
      //     padding: EdgeInsets.symmetric(horizontal: 50),
      //     child: ListView(
      //       children: [
      //         buildGenderField(),
      //         const SizedBox(height: 20),
      //         _MedicalHistoryCheckBox(),
      //         const SizedBox(height: 20),
      //         const DropdownMenu(
      //           label: Text('吸菸史'),
      //           dropdownMenuEntries: [
      //             DropdownMenuEntry(value: 'never', label: '從不吸菸'),
      //             DropdownMenuEntry(value: 'former', label: '曾經吸菸'),
      //             DropdownMenuEntry(value: 'not current', label: '目前沒有吸菸'),
      //             DropdownMenuEntry(value: 'current', label: '目前有吸菸'),
      //           ],
      //         ),
      //         const SizedBox(height: 20),
      //         TextFormField(
      //           keyboardType: TextInputType.number,
      //           decoration: const InputDecoration(
      //             labelText: '年齡',
      //             border: OutlineInputBorder(),
      //           ),
      //           validator: (value) {
      //             if (value == null || value.isEmpty) {
      //               return '必填';
      //             }
      //             return null;
      //           },
      //         ),
      //         const SizedBox(height: 20),
      //         TextFormField(
      //           validator: (value) {
      //             if (value == null || value.isEmpty) {
      //               return '必填';
      //             }
      //             return null;
      //           },
      //           decoration: const InputDecoration(
      //             labelText: 'BMI',
      //             border: OutlineInputBorder(),
      //           ),
      //         ),
      //         const SizedBox(height: 20),
      //         TextFormField(
      //           validator: (value) {
      //             if (value == null || value.isEmpty) {
      //               return '必填';
      //             }
      //             return null;
      //           },
      //           decoration: const InputDecoration(
      //             labelText: 'Hb1Ac',
      //             border: OutlineInputBorder(),
      //           ),
      //         ),
      //         const SizedBox(height: 20),
      //         TextFormField(
      //           validator: (value) {
      //             if (value == null || value.isEmpty) {
      //               return '必填';
      //             }
      //             return null;
      //           },
      //           decoration: const InputDecoration(
      //             labelText: '血糖值',
      //             border: OutlineInputBorder(),
      //           ),
      //         ),
      //         const SizedBox(height: 20),
      //         FilledButton.icon(
      //           onPressed: () {
      //             if (_formKey.currentState!.validate()) {
      //               log('test');
      //               _formKey.currentState!.save();
      //             }
      //           },
      //           style: util.filledPageButtonStyle(),
      //           icon: const Icon(Icons.send),
      //           label: const Text('提交'),
      //         ),
      //       ],
      //     ),
      //   ),
      // ),
    // );
  }

  Widget buildGenderField() {
    return FormField<String>(
      validator: (value) => value == null ? '請選擇性別' : null,
      builder: (field) {
        return Column(
          children: [
            const Text(
              '性別',
              style: TextStyle(fontSize: 20),
              textAlign: TextAlign.start,
            ),
            RadioListTile<String>(
              title: const Text('男'),
              value: 'male',
              groupValue: field.value,
              onChanged: field.didChange,
            ),
            RadioListTile<String>(
              title: const Text('女'),
              value: 'female',
              groupValue: field.value,
              onChanged: field.didChange,
            ),
            if (field.hasError)
              field.widget.errorBuilder!(field.context, field.errorText!),
          ],
        );
      },
      errorBuilder: (context, errorText) {
        return Text(errorText);
      },
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
