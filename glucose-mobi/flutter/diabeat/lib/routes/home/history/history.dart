import 'dart:developer';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:flutter/material.dart';

class _Record {
  _Record(dynamic data)
    : dateTime = DateTime.parse(data['created_at']).toLocal(),
      glucose = data['blood_glucose'],
      carb = data['carbohydrate_intake'],
      exercise = data['exercise_duration'],
      insulin = data['insulin_injection'];

  final DateTime dateTime;
  final double glucose;
  final double? carb;
  final double? exercise;
  final double? insulin;
}

class ChartPage extends StatefulWidget {
  const ChartPage({super.key});

  @override
  State<ChartPage> createState() => ChartPageState();
}

class ChartPageState extends State<ChartPage> {
  final Map<DateTime, List<_Record>> _records = {};
  final _today = () {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }();
  late DateTime _date = _today;

  @override
  Widget build(BuildContext context) {
    final thisDayRecord = _records[_date];

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            setState(() => _date = _date.subtract(const Duration(days: 1)));
          },
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
        centerTitle: true,
        title: TextButton(
          onPressed: () async {
            final dateTime = await showDatePicker(
              context: context,
              firstDate: DateTime(2024),
              lastDate: DateTime(3000),
            );

            if (dateTime != null) {
              setState(() => _date = dateTime);
            }
          },
          child: Text('${_date.year} / ${_date.month} / ${_date.day}'),
        ),
        actions: [
          IconButton(
            onPressed: () {
              setState(() => _date = _date.add(const Duration(days: 1)));
            },
            icon: const Icon(Icons.arrow_forward_ios_rounded),
          ),
        ],
      ),
      body: Stack(
        children: [
          ListView.builder(
            itemCount: thisDayRecord?.length,
            itemBuilder: (context, index) {
              if (thisDayRecord == null) return null;
              final item = thisDayRecord[index];
              final time = item.dateTime;

              final row0 = [
                _paddingText('血糖'),
                _paddingText(item.glucose.toString()),
                _paddingText('mg/dL'),
              ];

              final text1 = _paddingText('碳水');
              final row1 = item.carb == null
                  ? [text1, const SizedBox(), const SizedBox()]
                  : [
                      text1,
                      _paddingText(item.carb.toString()),
                      _paddingText('g'),
                    ];

              final text2 = _paddingText('運動');
              final row2 = item.exercise == null
                  ? [text2, const SizedBox(), const SizedBox()]
                  : [
                      text2,
                      _paddingText(item.exercise.toString()),
                      _paddingText('min'),
                    ];

              final text3 = _paddingText('胰島素');
              final row3 = item.insulin == null
                  ? [text3, const SizedBox(), const SizedBox()]
                  : [
                      text3,
                      _paddingText(item.insulin.toString()),
                      _paddingText('U'),
                    ];

              return Card.outlined(
                child: ListTile(
                  title: Text(
                    '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
                  ),
                  subtitle: Table(
                    columnWidths: {
                      0: IntrinsicColumnWidth(),
                      1: IntrinsicColumnWidth(),
                      2: FlexColumnWidth(),
                    },
                    children: [
                      TableRow(children: row0),
                      TableRow(children: row1),
                      TableRow(children: row2),
                      TableRow(children: row3),
                    ],
                  ),
                ),
              );
            },
          ),
          Positioned(
            bottom: 0,
            right: 0,
            child: FloatingActionButton.extended(
              onPressed: _getRecords,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('重新整理'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _getRecords() async {
    final result = await request.getRecords(context);
    if (!mounted) return;

    _records.clear();
    final multipleData = result.data;
    if (result.ok) {
      setState(() {
        for (final data in multipleData) {
          final record = _Record(data);
          _records
              .putIfAbsent(_onlyDate(record.dateTime), () => [])
              .add(record);
        }
      });
    } else {
      log('get records failed');
    }
  }
}

/* */
/* */
/* */

DateTime _onlyDate(DateTime dateTime) {
  return DateTime(dateTime.year, dateTime.month, dateTime.day);
}

Widget _paddingText(String text) {
  return Padding(padding: const EdgeInsets.only(right: 20), child: Text(text));
}
