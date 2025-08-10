import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class BloodFigurePage extends StatefulWidget {
  const BloodFigurePage({
    super.key,
    required this.goPrevPage,
    required this.goSendPage,
  });
  final void Function() goPrevPage;
  final void Function() goSendPage;

  @override
  State<BloodFigurePage> createState() => BloodFigurePageState();
}

class BloodFigurePageState extends State<BloodFigurePage> {
  final _formKey = GlobalKey<FormState>();
  final _hba1cFocus = FocusNode();
  double? glucose;
  double? hba1c;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextFormField(
            validator: util.stringValidator,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            onSaved: (newValue) => glucose = double.parse(newValue!),
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.next,
            onFieldSubmitted: (value) {
              _hba1cFocus.requestFocus();
            },
            decoration: const InputDecoration(
              labelText: '血糖 (mg/dL)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          TextFormField(
            focusNode: _hba1cFocus,
            validator: util.stringValidator,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            onSaved: (newValue) => hba1c = double.parse(newValue!),
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.done,
            decoration: const InputDecoration(
              labelText: 'HbA1c (%)',
              border: OutlineInputBorder(),
            ),
          ),
          const Spacer(),
          Row(
            children: [
              util.prevPageButton(widget.goPrevPage),
              const SizedBox(width: 20),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _trySend,
                  style: util.filledPageButtonStyle(),
                  icon: const Icon(Icons.send),
                  iconAlignment: IconAlignment.end,
                  label: const Text('送出'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _trySend() {
    final formState = _formKey.currentState!;
    if (formState.validate()) {
      formState.save();
      widget.goSendPage();
    }
  }
}
