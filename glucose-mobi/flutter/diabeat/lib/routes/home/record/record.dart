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
  final _glucoseMan = util.UDoubleFieldManager();
  final _carbohydrateMan = util.UDoubleFieldManager();
  final _exerciseMan = util.UDoubleFieldManager();
  final _insulinMan = util.UDoubleFieldManager();
  final _picker = ImagePicker();

  String? _glucoseErr;
  bool _submitted = false;
  bool _waiting = false;

  @override
  void dispose() {
    _glucoseMan.dispose();
    _carbohydrateMan.dispose();
    _exerciseMan.dispose();
    _insulinMan.dispose();
    super.dispose();
  }

  void _validateGlucose() {
    _glucoseErr = _glucoseMan.value == null ? '血糖不能為空' : null;
  }

  Future<void> _tryPostRecord() async {
    setState(() {
      _submitted = true;
      _validateGlucose();
      _waiting = _glucoseErr == null;
    });
    if (!_waiting) return;

    final result = await request.postRecord(
      context,
      glucose: _glucoseMan.value!,
      carbohydrate: _carbohydrateMan.value,
      exercise: _exerciseMan.value,
      insulin: _insulinMan.value,
    );

    setState(() => _waiting = false);

    if (result.ok) {
      _glucoseMan.clear();
      _carbohydrateMan.clear();
      _exerciseMan.clear();
      _insulinMan.clear();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('送出成功'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      //
    }
  }

  Future<void> _tryPredict() async {
    setState(() => _waiting = true);

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

    if (mounted && image != null) {
      final result = await request.predictCarbohydrate(context, image);
      _carbohydrateMan.text = (result.dataAsMap['predicted_value'] as double)
          .toStringAsFixed(1);
    }

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
                TextField(
                  controller: _glucoseMan.ctrl,
                  focusNode: _glucoseMan.focusNode,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  inputFormatters: const [util.UdoubleFormatter()],
                  textInputAction: TextInputAction.next,
                  onSubmitted: _carbohydrateMan.focus(),
                  decoration: InputDecoration(
                    labelText: '血糖 (mg/dL)',
                    errorText: _glucoseErr,
                    border: const OutlineInputBorder(),
                  ),
                  onChanged: (value) {
                    if (_submitted) {
                      setState(_validateGlucose);
                    }
                  },
                ),
                const SizedBox(height: 20),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _carbohydrateMan.ctrl,
                          focusNode: _carbohydrateMan.focusNode,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                          inputFormatters: const [util.UdoubleFormatter()],
                          textInputAction: TextInputAction.next,
                          onSubmitted: _exerciseMan.focus(),
                          decoration: InputDecoration(
                            labelText: '碳水攝取量 (g)',
                            border: const OutlineInputBorder(),
                          ),
                        ),
                      ),
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
                TextField(
                  controller: _exerciseMan.ctrl,
                  focusNode: _exerciseMan.focusNode,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  inputFormatters: const [util.UdoubleFormatter()],
                  textInputAction: TextInputAction.next,
                  onSubmitted: _insulinMan.focus(),
                  decoration: InputDecoration(
                    labelText: '運動時長 (min)',
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _insulinMan.ctrl,
                  focusNode: _insulinMan.focusNode,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  inputFormatters: const [util.UdoubleFormatter()],
                  textInputAction: TextInputAction.done,
                  decoration: InputDecoration(
                    labelText: '胰島素注射量 (U)',
                    border: const OutlineInputBorder(),
                  ),
                ),
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
}
