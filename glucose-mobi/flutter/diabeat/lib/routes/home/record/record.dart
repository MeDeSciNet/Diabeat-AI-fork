import 'package:diabeat/routes/connection/request.dart' as request;
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

class RecordPage extends StatefulWidget {
  const RecordPage({super.key});

  @override
  State<RecordPage> createState() => _RecordPageState();
}

class _RecordPageState extends State<RecordPage> {
  final _glucoseMeta = _UnsignedDoubleFieldMeta();
  final _carbohydrateMeta = _UnsignedDoubleFieldMeta();
  final _exerciseMeta = _UnsignedDoubleFieldMeta();
  final _insulinMeta = _UnsignedDoubleFieldMeta();
  String? _glucoseErr;

  bool _submitted = false;
  bool _waiting = false;

  @override
  void dispose() {
    _glucoseMeta.dispose();
    _carbohydrateMeta.dispose();
    _exerciseMeta.dispose();
    _insulinMeta.dispose();
    super.dispose();
  }

  void _validateGlucose() {
    _glucoseErr = _glucoseMeta.value == null ? '血糖不能為空' : null;
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
      glucose: _glucoseMeta.value!,
      carbohydrate: _carbohydrateMeta.value,
      exercise: _exerciseMeta.value,
      insulin: _insulinMeta.value,
    );

    setState(() => _waiting = false);

    if (result.ok) {
      _glucoseMeta.clear();
      _carbohydrateMeta.clear();
      _exerciseMeta.clear();
      _insulinMeta.clear();

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
    await request.predictCarbohydrate(context);
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
                  controller: _glucoseMeta.ctrl,
                  focusNode: _glucoseMeta.focusNode,
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [NonNegativeNumberFormatter()],
                  textInputAction: TextInputAction.next,
                  onSubmitted: _carbohydrateMeta.focus(context),
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
                          controller: _carbohydrateMeta.ctrl,
                          focusNode: _carbohydrateMeta.focusNode,
                          keyboardType: TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                          inputFormatters: [NonNegativeNumberFormatter()],
                          textInputAction: TextInputAction.next,
                          onSubmitted: _exerciseMeta.focus(context),
                          decoration: InputDecoration(
                            labelText: '碳水攝取量 (g)',
                            border: const OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      FilledButton(
                        onPressed: _tryPredict,
                        style: FilledButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(5),
                          ),
                        ),
                        child: const Icon(Icons.camera_alt),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _exerciseMeta.ctrl,
                  focusNode: _exerciseMeta.focusNode,
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [NonNegativeNumberFormatter()],
                  textInputAction: TextInputAction.next,
                  onSubmitted: _insulinMeta.focus(context),
                  decoration: InputDecoration(
                    labelText: '運動時長 (min)',
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _insulinMeta.ctrl,
                  focusNode: _insulinMeta.focusNode,
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [NonNegativeNumberFormatter()],
                  textInputAction: TextInputAction.done,
                  decoration: InputDecoration(
                    labelText: '胰島素注射量 (U)',
                    border: const OutlineInputBorder(),
                  ),
                ),
              ],
            ),
            const Spacer(),
            FilledButton(
              onPressed: _waiting ? null : _tryPostRecord,
              style: PageButtons.filled,
              child: const Text('送出'),
            ),
            const Spacer(),
          ],
        ),
      ),
    );
  }
}

class _UnsignedDoubleFieldMeta {
  final ctrl = TextEditingController();
  final focusNode = FocusNode();

  double? get value => double.tryParse(ctrl.text);
  set value(double? value) {
    ctrl.text = value?.toString() ?? '';
  }

  void dispose() {
    ctrl.dispose();
    focusNode.dispose();
  }

  void Function(String) focus(BuildContext context) {
    return (value) {
      FocusScope.of(context).requestFocus(focusNode);
    };
  }

  void clear() {
    ctrl.clear();
  }
}
