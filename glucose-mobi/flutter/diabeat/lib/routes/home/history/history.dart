import 'dart:convert';
import 'dart:developer';
import 'package:csv/csv.dart';
import 'package:diabeat/routes/home/history/pdf_csv_dialog.dart';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:pdf/widgets.dart' as pw;

class _Record {
  _Record(dynamic data)
    : dateTime = DateTime.parse(data['created_at']).toLocal(),
      glucose = data['blood_glucose'],
      carbs = data['carbohydrate_intake'],
      exercise = data['exercise_duration'],
      insulin = data['insulin_injection'];

  List<String?> toCsvRow() {
    return [
      util.humanDate(dateTime),
      util.humanTime(dateTime),
      glucose.toString(),
      carbs?.toString(),
      exercise?.toString(),
      insulin?.toString(),
    ];
  }

  final DateTime dateTime;
  final double glucose;
  final double? carbs;
  final double? exercise;
  final double? insulin;
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => HistoryPageState();
}

class HistoryPageState extends State<HistoryPage> {
  final _csvSerializer = const ListToCsvConverter();
  final _records = <DateTime, List<_Record>>{};
  final _firstDate = DateTime(2024);
  var _date = _todayDate();

  @override
  void initState() {
    // fix timeout problem
    getRecords(goToToday: true);
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final thisDayRecord = _records[_date];

    return Scaffold(
      appBar: AppBar(
        leading: _date == _firstDate
            ? null
            : IconButton(
                onPressed: () {
                  setState(
                    () => _date = _date.subtract(const Duration(days: 1)),
                  );
                },
                icon: const Icon(Icons.arrow_back_rounded),
              ),
        centerTitle: true,
        title: TextButton(
          onPressed: () async {
            final dateTime = await showDatePicker(
              context: context,
              firstDate: _firstDate,
              lastDate: _todayDate(),
              initialDate: _date,
            );

            if (dateTime != null) {
              setState(() => _date = dateTime);
            }
          },
          style: util.filledPageButtonStyle(),
          child: Text(util.humanDate(_date)),
        ),
        actions: [
          if (_date != _todayDate())
            IconButton(
              onPressed: () {
                setState(() => _date = _date.add(const Duration(days: 1)));
              },
              icon: const Icon(Icons.arrow_forward_rounded),
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.only(left: 20, right: 20, bottom: 20),
        child: Stack(
          children: [
            ListView.separated(
              itemCount: thisDayRecord?.length ?? 0,
              separatorBuilder: (context, index) => SizedBox(height: 10),
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
                final row1 = item.carbs == null
                    ? [text1, const SizedBox(), const SizedBox()]
                    : [
                        text1,
                        _paddingText(item.carbs.toString()),
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
                    title: Text(util.humanTime(time)),
                    subtitle: Table(
                      columnWidths: const {
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
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  FloatingActionButton.extended(
                    heroTag: '#getRecords',
                    onPressed: () {
                      getRecords(goToToday: true);
                    },
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('重新整理'),
                  ),
                  const SizedBox(height: 20),
                  FloatingActionButton.extended(
                    heroTag: '#export',
                    onPressed: _export,
                    icon: const Icon(Icons.ios_share_rounded),
                    label: const Text('匯出紀錄'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> getRecords({required bool goToToday}) async {
    final (ok, multiData) = await request.getRecords(context);
    if (!mounted) return;

    _records.clear();
    if (ok) {
      setState(() {
        for (final data in multiData) {
          final record = _Record(data);
          _records
              .putIfAbsent(_onlyDate(record.dateTime), () => [])
              .add(record);

          if (goToToday) {
            _date = _todayDate();
          }
        }
      });
    } else {
      log('get records failed');
    }
  }

  Future<void> _export() async {
    final nav = await PdfCsvDialog.show(context);
    if (nav == null) return;

    final csvTable = <List<String?>>[
      [
        'Date',
        'Time',
        'Glucose (mg/dL)',
        'Carbs (g)',
        'Exercise (min)',
        'Insulin (U)',
      ],
    ];

    for (final theDayRecords in _records.values) {
      for (final record in theDayRecords) {
        csvTable.add(record.toCsvRow());
      }
    }

    final filename =
        '${session.username}_DiabeatHistory_${DateTime.now().toIso8601String()}';

    final ShareParams shareParams;
    switch (nav) {
      case PdfCsvEnum.pdf:
        {
          final pdf = pw.Document();

          pdf.addPage(
            pw.Page(
              margin: pw.EdgeInsets.all(10),
              build: (pw.Context context) {
                return pw.Table(
                  children: csvTable.map((row) {
                    return pw.TableRow(
                      children: row
                          .map((e) => e == null ? pw.SizedBox() : pw.Text(e))
                          .toList(),
                    );
                  }).toList(),
                );
              },
            ),
          );

          final bytes = await pdf.save();
          shareParams = ShareParams(
            files: [XFile.fromData(bytes, mimeType: 'application/pdf')],
            fileNameOverrides: ['$filename.pdf'],
          );

          break;
        }

      case PdfCsvEnum.csv:
        {
          final csvString = _csvSerializer
              .convert(csvTable)
              .replaceAll('null', '');
          final bytes = utf8.encode(csvString);
          shareParams = ShareParams(
            files: [XFile.fromData(bytes, mimeType: 'text/csv')],
            fileNameOverrides: ['$filename.csv'],
          );

          break;
        }
    }

    await SharePlus.instance.share(shareParams);
  }
}

/* */
/* */
/* */

Widget _paddingText(String text) {
  return Padding(padding: const EdgeInsets.only(right: 20), child: Text(text));
}

DateTime _onlyDate(DateTime dateTime) {
  return DateTime(dateTime.year, dateTime.month, dateTime.day);
}

DateTime _todayDate() {
  return _onlyDate(DateTime.now());
}
