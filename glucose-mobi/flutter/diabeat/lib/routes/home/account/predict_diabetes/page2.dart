import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page2 extends StatefulWidget {
  const Page2({super.key, required this.goPrevPage, required this.goSendPage});
  final void Function() goPrevPage;
  final void Function() goSendPage;

  @override
  State<Page2> createState() => Page2State();
}

class Page2State extends State<Page2> {
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
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => glucose = double.parse(newValue!),
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.next,
            onFieldSubmitted: (value) {
              _hba1cFocus.requestFocus();
            },
            decoration: util.inputBorder('血糖 (mg/dL)'),
          ),
          const SizedBox(height: 20),
          TextFormField(
            focusNode: _hba1cFocus,
            validator: util.nonEmptyValidator,
            onSaved: (newValue) => hba1c = double.parse(newValue!),
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            inputFormatters: const [util.UdoubleFormatter()],
            textInputAction: TextInputAction.done,
            decoration: util.inputBorder('HbA1c (%)'),
          ),
          const Spacer(),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: widget.goPrevPage,
                  style: util.outlinedPageButtonStyle(),
                  icon: const Icon(Icons.arrow_back_ios_new),
                  label: const Text('上一頁'),
                ),
              ),
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
