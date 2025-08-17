import 'dart:convert';
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
  DateTime _date = _todayDate();
  bool _waitingRefresh = false;
  bool _waitingMakeDumps = false;

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
                  util.paddingText('血糖'),
                  util.paddingText(item.glucose.toString()),
                  util.paddingText('mg/dL'),
                ];

                final text1 = util.paddingText('碳水');
                final row1 = item.carbs == null
                    ? [text1, const SizedBox(), const SizedBox()]
                    : [
                        text1,
                        util.paddingText(item.carbs.toString()),
                        util.paddingText('g'),
                      ];

                final text2 = util.paddingText('運動');
                final row2 = item.exercise == null
                    ? [text2, const SizedBox(), const SizedBox()]
                    : [
                        text2,
                        util.paddingText(item.exercise.toString()),
                        util.paddingText('min'),
                      ];

                final text3 = util.paddingText('胰島素');
                final row3 = item.insulin == null
                    ? [text3, const SizedBox(), const SizedBox()]
                    : [
                        text3,
                        util.paddingText(item.insulin.toString()),
                        util.paddingText('U'),
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
                    heroTag:
                        '#getRecords', // idk why this necessary when have multiple FABs
                    onPressed: _waitingRefresh
                        ? null
                        : () {
                            getRecords(goToToday: true);
                          },
                    icon: _waitingRefresh
                        ? util.smallCircularProgressIndicator()
                        : const Icon(Icons.refresh_rounded),
                    label: _waitingRefresh
                        ? const Text('更新紀錄中')
                        : const Text('重新整理'),
                  ),
                  const SizedBox(height: 20),
                  FloatingActionButton.extended(
                    heroTag: '#export',
                    onPressed: _waitingMakeDumps
                        ? null
                        : () async {
                            final nav = await PdfCsvDialog.show(context);
                            if (nav == null) return;

                            setState(() => _waitingMakeDumps = true);
                            await _export(nav);
                            setState(() => _waitingMakeDumps = false);
                          },
                    icon: _waitingMakeDumps
                        ? util.smallCircularProgressIndicator()
                        : const Icon(Icons.ios_share_rounded),
                    label: _waitingMakeDumps
                        ? const Text('製作中')
                        : const Text('匯出紀錄'),
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
    setState(() => _waitingRefresh = true);

    final (ok, multiData) = await request.getRecords(context);
    if (!mounted) return;

    if (ok) {
      setState(() {
        _waitingRefresh = false;

        _records.clear();
        for (final data in multiData) {
          final record = _Record(data);
          _records
              .putIfAbsent(_onlyDate(record.dateTime), () => [])
              .add(record);
        }

        if (goToToday) {
          _date = _todayDate();
        }
      });
    } else {
      setState(() => _waitingRefresh = false);
    }
  }

  Future<void> _export(PdfCsvEnum nav) async {
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
            pw.MultiPage(
              maxPages: 10000,
              margin: const pw.EdgeInsets.all(20),
              build: (pw.Context context) => [
                pw.TableHelper.fromTextArray(data: csvTable),
              ],
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

DateTime _onlyDate(DateTime dateTime) {
  return DateTime(dateTime.year, dateTime.month, dateTime.day);
}

DateTime _todayDate() {
  return _onlyDate(DateTime.now());
}
