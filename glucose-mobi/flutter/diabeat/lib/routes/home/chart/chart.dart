import 'dart:developer';

import 'package:diabeat/routes/network/request.dart' as request;
import 'package:flutter/material.dart';

class ChartPage extends StatefulWidget {
  const ChartPage({super.key});

  @override
  State<ChartPage> createState() => ChartPageState();
}

class ChartPageState extends State<ChartPage> {
  List? _data;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Stack(
        children: [
          Column(
            children: [
              TextButton(
                onPressed: () {
                  showDatePicker(
                    context: context,
                    firstDate: DateTime(1970),
                    lastDate: DateTime(2038),
                  );
                },
                child: Text('6/3'),
              ),
              Expanded(
                child: ListView.builder(
                  itemCount: _data?.length,
                  itemBuilder: (context, index) {
                    if (_data == null) return null;
                    final item = _data![index];
                    final time = DateTime.parse(item['created_at']).toLocal();

                    final glucose = item['blood_glucose'];
                    final glucoseRow = glucose == null
                        ? const [
                            Text('血糖'),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                          ]
                        : [
                            const Text('血糖'),
                            const SizedBox(width: 20),
                            Text(glucose.toString()),
                            const SizedBox(width: 20),
                            const Text('mg/dL'),
                          ];

                    final carbs = item['carbohydrate_intake'];
                    final carbsRow = carbs == null
                        ? const [
                            Text('碳水'),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                          ]
                        : [
                            Text('碳水'),
                            const SizedBox(width: 20),
                            Text(carbs.toString()),
                            const SizedBox(width: 20),
                            const Text('g'),
                          ];

                    final exercise = item['exercise_duration'];
                    final exerciseRow = exercise == null
                        ? const [
                            Text('運動'),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                          ]
                        : [
                            const Text('運動'),
                            const SizedBox(width: 20),
                            Text(exercise.toString()),
                            const SizedBox(width: 20),
                            const Text('min'),
                          ];

                    final insulin = item['insulin_injection'];
                    final insulinRow = insulin == null
                        ? const [
                            Text('胰島素'),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                            SizedBox(),
                          ]
                        : [
                            const Text('胰島素'),
                            const SizedBox(width: 20),
                            Text(insulin.toString()),
                            const SizedBox(width: 20),
                            const Text('U'),
                          ];

                    return Card.outlined(
                      child: ListTile(
                        title: Text('${time.hour}:${time.minute}'),
                        subtitle: Table(
                          columnWidths: {
                            0: IntrinsicColumnWidth(),
                            1: IntrinsicColumnWidth(),
                            2: IntrinsicColumnWidth(),
                            3: IntrinsicColumnWidth(),
                            4: FlexColumnWidth(),
                          },
                          children: [
                            TableRow(children: glucoseRow),
                            TableRow(children: carbsRow),
                            TableRow(children: exerciseRow),
                            TableRow(children: insulinRow),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
          Positioned(
            bottom: 20,
            right: 20,
            child: FloatingActionButton.extended(
              onPressed: () async {
                final result = await request.getRecords(context);
                if (!mounted) return;

                if (result.ok) {
                  setState(() => _data = result.data);
                } else {
                  log('get records failed');
                }
              },
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('刷新'),
            ),
          ),
        ],
      ),
    );
  }
}
