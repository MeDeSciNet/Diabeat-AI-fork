package rl.collab.diabeat.frag

import android.graphics.Color
import android.view.View
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import rl.collab.diabeat.R
import rl.collab.diabeat.Result
import rl.collab.diabeat.databinding.FragChartBinding


class ChartFrag : MyFrag<FragChartBinding>(FragChartBinding::inflate) {
    private lateinit var adapter: MyAdapter

    override fun FragChartBinding.setView() {
        adapter = MyAdapter(layoutInflater, vm.records)
        table.adapter = adapter

        segBtnGroup.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (!isChecked)
                return@addOnButtonCheckedListener

            if (checkedId == R.id.chart_btn) {
                table.visibility = View.INVISIBLE
                chart.visibility = View.VISIBLE
            } else {
                chart.visibility = View.INVISIBLE
                table.visibility = View.VISIBLE
            }
        }
        chartBtn.setOnClickListener {
            if (segBtnGroup.checkedButtonId == R.id.chart_btn)
                getRecords()
        }
        tableBtn.setOnClickListener {
            if (segBtnGroup.checkedButtonId == R.id.table_btn)
                getRecords()
        }

        swipeRefresh.isEnabled = vm.acc != null
        swipeRefresh.setOnRefreshListener { getRecords() }

        getRecords()
    }

    private fun FragChartBinding.getRecords() {
        vm.acc ?: return

        val onSucceed = { r: List<Result.Records> ->
            vm.records.clear()
            vm.records.addAll(r)

            if (table.visibility == View.VISIBLE)
                adapter.notifyDataSetChanged()
            else {
                val entries = mutableListOf<Entry>()
                for ((i, it) in r.reversed().withIndex())
                    entries.add(Entry(i.toFloat(), it.blood_glucose.toFloat()))

                val dataSet = LineDataSet(entries, "")
                dataSet.valueTextColor = Color.RED
                chart.data = LineData(dataSet)
                chart.invalidate()
            }
            swipeRefresh.isRefreshing = false
        }
        request(onSucceed, null, null, false) { getRecords(vm.access!!) }
    }
}