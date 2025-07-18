package rl.collab.diabeat.frag

import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import rl.collab.diabeat.Request
import rl.collab.diabeat.Result
import rl.collab.diabeat.databinding.DiaSrcBinding
import rl.collab.diabeat.databinding.FragRecordBinding
import rl.collab.diabeat.str
import java.io.File

class RecordFrag : MyFrag<FragRecordBinding>(FragRecordBinding::inflate) {
    private lateinit var takePicFilename: String
    private lateinit var takePicUri: Uri
    private val takePicLauncher = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (!success)
            return@registerForActivityResult

        toastSizeReturnName(takePicUri)
        val byteArr = resolver.openInputStream(takePicUri)!!.readBytes()
        val obj = byteArr.toRequestBody("image/jpeg".toMediaType())
        val image = MultipartBody.Part.createFormData("image", takePicFilename, obj)
        predictCarbohydrate(image)
    }
    private val pickImageLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri ?: return@registerForActivityResult

        val filename = toastSizeReturnName(uri)
        val byteArr = resolver.openInputStream(uri)!!.readBytes()
        val obj = byteArr.toRequestBody("image/*".toMediaType())
        val image = MultipartBody.Part.createFormData("image", filename, obj)
        predictCarbohydrate(image)
    }

    private fun toastSizeReturnName(uri: Uri): String {
        var fileSize = 0L
        var filename = ""

        val cursor = resolver.query(uri, null, null, null, null)
        cursor?.use {
            it.moveToFirst()
            fileSize = it.getLong(it.getColumnIndexOrThrow(OpenableColumns.SIZE))
            filename = it.getString(it.getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME))
        }

        toast(
            if (fileSize > 1048576)
                "上傳 %.1f MB".format(fileSize / 1048576.0)
            else
                "上傳 %.1f KB".format(fileSize / 1024.0)
        )

        return filename
    }

    override fun FragRecordBinding.setView() {
        saveBtn.setOnClickListener {
            vm.acc ?: run {
                toast("請先登入🔑")
                return@setOnClickListener
            }

            if (glucoseEt.str.isEmpty()) {
                toast("血糖值不能為空❗")
                return@setOnClickListener
            }

            val obj = Request.Record(
                glucoseEt.str.toDouble(),
                carbohydrateEt.str.toDoubleOrNull(),
                exerciseEt.str.toDoubleOrNull(),
                insulinEt.str.toDoubleOrNull()
            )
            postRecords(obj)
        }

        predictCarbohydrateBtn.setOnClickListener {
            vm.acc ?: run {
                toast("請先登入🔑")
                return@setOnClickListener
            }

            rq(DiaSrcBinding::inflate) {
                val dialog = dialog("選擇來源", view = root, pos = null, neg = null, cancelable = true)
                photoTv.setOnClickListener {
                    pickImageLauncher.launch("image/*")
                    dialog.dismiss()
                }
                cameraTv.setOnClickListener {
                    takePicFilename = "${System.currentTimeMillis()}.jpg"
                    val file = File(con.cacheDir, takePicFilename)
                    takePicUri = FileProvider.getUriForFile(con, "rl.collab.diabeat.fileprovider", file)
                    takePicLauncher.launch(takePicUri)
                    dialog.dismiss()
                }
            }
        }
    }

    private fun enableBtns(b: Boolean) {
        binding.saveBtn.isEnabled = b
        binding.predictCarbohydrateBtn.isEnabled = b
    }

    private fun postRecords(obj: Request.Record) {
        enableBtns(false)

        val onSucceed = { _: Result.Records ->
            toast("已儲存✅")
            binding.run {
                glucoseEt.str = ""
                carbohydrateEt.str = ""
                exerciseEt.str = ""
                insulinEt.str = ""
                etGroup.clearFocus()
            }
            enableBtns(true)
        }
        val onFail = {
            enableBtns(true)
        }
        request(onSucceed, null, onFail, false) { postRecord(vm.access!!, obj) }
    }

    private fun predictCarbohydrate(image: MultipartBody.Part) {
        enableBtns(false)

        val onSucceed = { r: Result.Predict ->
            binding.carbohydrateEt.str = "%.0f".format(r.predicted_value)
            enableBtns(true)
        }
        val onFail = {
            enableBtns(true)
        }
        request(onSucceed, null, onFail, false) { predictCarbohydrate(vm.access!!, image) }
    }
}