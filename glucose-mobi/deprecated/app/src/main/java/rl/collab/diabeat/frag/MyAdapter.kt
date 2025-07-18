package rl.collab.diabeat.frag

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import rl.collab.diabeat.Result
import rl.collab.diabeat.databinding.TableCellBinding
import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class MyAdapter(private val layoutInflater: LayoutInflater, private val data: List<Result.Records>) : BaseAdapter() {

    class MyViewHolder(val binding: TableCellBinding) {
        init {
            binding.root.tag = this
        }
    }

    private fun String.toLocalTime(): String {
        val zone = Instant.parse(this).atZone(ZoneId.systemDefault())
        val now = ZonedDateTime.now()
        val pattern = when {
            zone.toLocalDate() == now.toLocalDate() -> "HH:mm"
            zone.year == now.year -> "MM/dd HH:mm"
            else -> "yyyy/MM/dd HH:mm:ss"
        }
        return zone.format(DateTimeFormatter.ofPattern(pattern))
    }

    private fun Double?.tryToStr() =
        if (this == null) "-"
        else if (this % 1.0 == 0.0) toInt().toString()
        else "%.1f".format(this)

    override fun getCount() = (1 + data.size) * 5

    override fun getItem(i: Int): String {
        val row = i / 5 - 1
        return when (i % 5) {
            0 -> if (i < 5) "時間" else data[row].created_at.toLocalTime()
            1 -> if (i < 5) "血糖" else data[row].blood_glucose.tryToStr()
            2 -> if (i < 5) "碳水" else data[row].carbohydrate_intake.tryToStr()
            3 -> if (i < 5) "運動" else data[row].exercise_duration.tryToStr()
            4 -> if (i < 5) "胰島素" else data[row].insulin_injection.tryToStr()
            else -> ""
        }
    }

    override fun getItemId(i: Int) = i.toLong()

    override fun getView(i: Int, convertView: View?, parent: ViewGroup?): View {
        val holder = if (convertView == null)
            MyViewHolder(TableCellBinding.inflate(layoutInflater, parent, false))
        else
            convertView.tag as MyViewHolder

        holder.binding.tv.text = getItem(i)

        return holder.binding.root
    }
}