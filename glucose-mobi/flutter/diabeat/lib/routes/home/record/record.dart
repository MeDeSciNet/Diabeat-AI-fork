import 'dart:developer';
import 'package:diabeat/routes/home/record/image_picker_dialog.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

enum PostStateEnum { never, posted, none }

class RecordPage extends StatefulWidget {
  const RecordPage({super.key});

  @override
  State<RecordPage> createState() => RecordPageState();
}

class RecordPageState extends State<RecordPage> {
  final _managers = [
    _UdoubleFieldManager('血糖 (mg/dL)'),
    _UdoubleFieldManager('碳水攝取量 (g)'),
    _UdoubleFieldManager('運動時長 (min)'),
    _UdoubleFieldManager('胰島素注射量 (U)'),
  ];
  final _picker = ImagePicker();
  bool _waiting = false;
  var postState = PostStateEnum.never;

  @override
  void dispose() {
    for (final man in _managers) {
      man.controller.dispose();
      man.focusNode.dispose();
    }
    super.dispose();
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
                        icon: const Icon(Icons.camera_alt_rounded),
                        label: const Text('AI 估算'),
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
              icon: const Icon(Icons.send_rounded),
              label: const Text('送出'),
            ),
            const Spacer(),
          ],
        ),
      ),
    );
  }

  Future<void> _tryPostRecord() async {
    setState(() => _waiting = true);

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

      postState = PostStateEnum.posted;
    } else {
      log('post record failed');
    }
  }

  Future<void> _tryPredict() async {
    final source = await ImagePickerDialog.show(context);
    if (source == null) return;

    final image = await _picker.pickImage(source: source);
    if (image == null || !mounted) return;
    setState(() => _waiting = true);

    final result = await request.predictCarb(context, image);
    if (!mounted) return;

    if (result.ok) {
      final value = result.data['predicted_value'] as double;
      _managers[1].controller.text = value.toStringAsFixed(1);
    } else {
      log('predict carb failed');
    }

    if (!mounted) return;
    setState(() => _waiting = false);
  }

  Widget _uDoubleFormField(int index) {
    final man = _managers[index];
    final isFirst = index == 0;
    final isLast = index == 3;

    return TextFormField(
      validator: isFirst ? util.nonEmptyValidator : null,
      controller: man.controller,
      focusNode: man.focusNode,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: const [util.UdoubleFormatter()],
      textInputAction: isLast ? TextInputAction.done : TextInputAction.next,
      onFieldSubmitted: isLast
          ? null
          : (value) {
              _managers[index + 1].focusNode.requestFocus();
            },
      decoration: util.inputBorder(man.labelText),
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
