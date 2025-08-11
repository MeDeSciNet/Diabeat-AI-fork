import 'package:diabeat/routes/network/dialog/image_picker_dialog.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class RecordPage extends StatefulWidget {
  const RecordPage({super.key});

  @override
  State<RecordPage> createState() => _RecordPageState();
}

class _RecordPageState extends State<RecordPage> {
  final _managers = [
    _UdoubleFieldManager('血糖 (mg/dL)'),
    _UdoubleFieldManager('碳水攝取量 (g)'),
    _UdoubleFieldManager('運動時長 (min)'),
    _UdoubleFieldManager('胰島素注射量 (U)'),
  ];
  final _picker = ImagePicker();
  bool _waiting = false;

  @override
  void dispose() {
    for (final man in _managers) {
      man.controller.dispose();
      man.focusNode.dispose();
    }
    super.dispose();
  }

  Future<void> _tryPostRecord() async {
    final result = await request.postRecord(
      context,
      glucose: _managers[0].value!,
      carbohydrate: _managers[1].value,
      exercise: _managers[2].value,
      insulin: _managers[3].value,
    );

    if (!mounted) return;
    setState(() => _waiting = false);

    if (result.ok) {
      for (final man in _managers) {
        man.controller.clear();
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('送出成功'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      // result.failed
    }
  }

  Future<void> _tryPredict() async {
    final nav = await ImagePickerDialog.show(context);
    final image = switch (nav) {
      ImagePickerDialogNav.camera => await _picker.pickImage(
        source: ImageSource.camera,
      ),
      ImagePickerDialogNav.gallery => await _picker.pickImage(
        source: ImageSource.gallery,
      ),
      _ => null,
    };

    if (!mounted) return;
    setState(() => _waiting = true);

    if (image != null) {
      final result = await request.predictCarbohydrate(context, image);

      if (result.ok) {
        final value = result.dataAsMap['predicted_value'] as double;
        _managers[1].controller.text = value.toStringAsFixed(1);
      } else {
        // result.failed
      }
    }

    if (!mounted) return;
    setState(() => _waiting = false);
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: 50),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Spacer(),
            const Text(
              '紀錄',
              style: TextStyle(fontSize: 35),
              textAlign: TextAlign.center,
            ),
            const Spacer(),
            Column(
              children: [
                _uDoubleFormField(0),
                const SizedBox(height: 20),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(child: _uDoubleFormField(1)),
                      const SizedBox(width: 10),
                      FilledButton.icon(
                        onPressed: _waiting ? null : _tryPredict,
                        style: util.filledPageButtonStyle(),
                        icon: const Icon(Icons.auto_awesome),
                        label: const Text('預測'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                _uDoubleFormField(2),
                const SizedBox(height: 20),
                _uDoubleFormField(3),
              ],
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: _waiting ? null : _tryPostRecord,
              style: util.filledPageButtonStyle(),
              icon: const Icon(Icons.send),
              label: const Text('送出'),
            ),
            const Spacer(),
          ],
        ),
      ),
    );
  }

  Widget _uDoubleFormField(int index) {
    return TextFormField(
      validator: index == 0 ? util.nonEmptyValidator : null,
      autovalidateMode: AutovalidateMode.onUnfocus,
      controller: _managers[index].controller,
      focusNode: _managers[index].focusNode,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: const [util.UdoubleFormatter()],
      textInputAction: index == 3 ? TextInputAction.done : TextInputAction.next,
      onFieldSubmitted: index == 3
          ? null
          : (value) {
              _managers[index + 1].focusNode.requestFocus();
            },
      decoration: util.inputBorder('碳水攝取量 (g)'),
    );
  }
}

class _UdoubleFieldManager {
  _UdoubleFieldManager(this.labelText);

  final controller = TextEditingController();
  final focusNode = FocusNode();
  final String labelText;

  double? get value => double.tryParse(controller.text);
}
