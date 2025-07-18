package rl.collab.diabeat

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.content.edit
import com.google.android.material.dialog.MaterialAlertDialogBuilder

fun nacho(vararg msg: Any?) =
    Log.d("nacho", msg.joinToString(" "))

var EditText.str
    get() = text.toString()
    set(value) = setText(value)

val AlertDialog.pos
    get() = getButton(AlertDialog.BUTTON_POSITIVE)!!

val AlertDialog.neu
    get() = getButton(AlertDialog.BUTTON_NEUTRAL)!!

fun Context.toast(msg: String) =
    Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

fun Context.dialog(
    title: String,
    msg: String? = null,
    view: View? = null,
    pos: String? = "OK",
    neg: String? = "取消",
    neutral: String? = null,
    cancelable: Boolean = false
) =
    MaterialAlertDialogBuilder(this)
        .setTitle(title)
        .setMessage(msg)
        .setView(view)
        .setPositiveButton(pos, null)
        .setNegativeButton(neg, null)
        .setNeutralButton(neutral, null)
        .setCancelable(cancelable)
        .show()!!

inline fun SharedPreferences.syncEdit(action: SharedPreferences.Editor.() -> Unit) =
    edit(true, action)