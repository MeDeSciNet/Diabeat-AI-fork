import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page0 extends StatefulWidget {
  const Page0({super.key, required this.goNextPage});
  final void Function() goNextPage;

  @override
  State<Page0> createState() => Page0State();
}

class Page0State extends State<Page0> {
  final _formKey = GlobalKey<FormState>();
  final _heightFocus = FocusNode();
  final _weightFocus = FocusNode();
  String? gender;
  int? age;
  double? height;
  double? weight;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FormField<String>(
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => gender = newValue,
            builder: (field) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text.rich(
                  TextSpan(
                    text: '性別 ',
                    children: [
                      if (field.hasError)
                        TextSpan(
                          text: '(必填)',
                          style: const TextStyle(color: Colors.red),
                        ),
                    ],
                  ),
                ),
                RadioListTile(
                  title: const Text('男'),
                  value: 'male',
                  groupValue: field.value,
                  onChanged: field.didChange,
                ),
                RadioListTile(
                  title: const Text('女'),
                  value: 'female',
                  groupValue: field.value,
                  onChanged: field.didChange,
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          TextFormField(
            keyboardType: TextInputType.number,
            textInputAction: TextInputAction.next,
            onFieldSubmitted: (value) {
              _heightFocus.requestFocus();
            },
            decoration: util.inputBorder('年齡'),
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => age = int.parse(newValue!),
          ),
          const SizedBox(height: 20),
          TextFormField(
            focusNode: _heightFocus,
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.next,
            onFieldSubmitted: (value) {
              _weightFocus.requestFocus();
            },
            decoration: util.inputBorder('身高 (cm)'),
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => height = double.parse(newValue!),
          ),
          const SizedBox(height: 20),
          TextFormField(
            focusNode: _weightFocus,
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.go,
            onFieldSubmitted: (value) {
              _tryGoNextPage();
            },
            decoration: util.inputBorder('體重 (kg)'),
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => weight = double.parse(newValue!),
          ),
          const Spacer(),
          Row(
            children: [
              const Spacer(),
              const SizedBox(width: 20),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _tryGoNextPage,
                  style: util.filledPageButtonStyle(),
                  icon: const Icon(Icons.arrow_forward_rounded),
                  iconAlignment: IconAlignment.end,
                  label: const Text('下一頁'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _tryGoNextPage() {
    final formState = _formKey.currentState!;
    if (formState.validate()) {
      formState.save();
      widget.goNextPage();
    }
  }
}
